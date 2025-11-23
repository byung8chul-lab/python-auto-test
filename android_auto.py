import pytest
import time
import requests
import os
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from datetime import datetime, timedelta

@pytest.fixture(scope="session")
def driver():
    """각 테스트 실행 시 새로운 Appium WebDriver 인스턴스를 생성"""
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.platform_version = "16"
    options.device_name = "emulator-5554"  # 기기 이름 (SM-F731N)
    options.app_package = "com.baropharm.app.dev"
    options.app_activity = "com.baropharm.app.ui.view.getstarted.GetStartedActivity"

    # Appium 서버와 연결
    driver = webdriver.Remote("http://localhost:4723", options=options)
    yield driver
    driver.quit()

#------------------------------인증값 저장------------------------------------------------------------------------------------------------
def get_access_token():
    login_url = "https://api-v2.dev.barodev.com/auth/v2/token"
    payload = {
        "username": "barocooper@naver.com",
        "password": "baro1234!"
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(login_url, json=payload, headers=headers)
    print("\nstatus", response.status_code)

    if response.status_code == 200:
        access_token = response.json().get("access")
        print("accesstoken:", access_token)
        return access_token
    else:
        raise Exception("로그인실패")
    
def get_recent_orders(token, after_time):
    url = "https://api-v2.dev.barodev.com/me/orders"
    headrs = {
        "Authorization": f"Baro {token}"
    }
    params = {
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "end_date": datetime.now().strftime("%Y-%m-%d"),
        "page": 1,
        "per_page": 50
    }
    response = requests.get(url, headers=headrs, params=params)

    if response.status_code == 200:
        orders = response.json().get("items", [])
        #특정 시간 이후 필터링
        recent_orders = [
            order for order in orders
            if datetime.strptime(order["order_datetime"], "%Y-%m-%d %H:%M:%S") >= after_time
        ]
        return recent_orders
    else:
        print("주문조회실패", response.status_code, response.text)
        return[]



#---------------- 스크롤 및 uiselector 선택용--------------------------------------------------------------------------------------------------------------
def scroll_to_element_by_id(driver, element_id):
        try:
            #특정 Id가 나올때까지 스크롤하는 메소드
            driver.find_element(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().resourceId("{element_id}"))'
            )    
            print(f"요소 '{element_id}'를 찾았습니다.")
            time.sleep(1)
        except Exception as e:
            print(f"Error during scroling to element '{element_id}' : {e}")

def scroll_to_element_by_partial_text(driver, partial_text: str, retries: int = 3):
    """
    NestedScrollView 안에서 텍스트 일부가 포함된 요소를 찾을 때까지 스크롤하는 함수

    :param driver: Appium WebDriver
    :param partial_text: 텍스트 일부 (ex: "프리미엄 제약")
    :param retries: 재시도 횟수
    """
    scroll_class = "androidx.core.widget.NestedScrollView"
    command = (
        f'new UiScrollable(new UiSelector().className("{scroll_class}"))'
        f'.scrollIntoView(new UiSelector().textContains("{partial_text}"))'
    )

    for attempt in range(retries):
        try:
            driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, command)
            print(f"[시도 {attempt + 1}] '{partial_text}' 포함된 요소를 찾았습니다.")
            return
        except Exception as e:
            print(f"[시도 {attempt + 1}] 스크롤 실패: {e}")
            time.sleep(1)

    raise Exception(f"'{partial_text}' 포함된 요소를 {retries}회 시도했지만 찾지 못했습니다.")

def scroll_until_element_found(driver, element_id, max_scrolls=10, direction="down", swipe_duration=800):
    """
    특정 element_id 값이 화면에 보일 때까지 스크롤하는 함수.

    :param driver: Appium WebDriver 인스턴스
    :param element_id: 찾을 요소의 resource-id
    :param max_scrolls: 최대 스크롤 횟수 (기본값 10)
    :param direction: 스크롤 방향 ("down" / "up")
    :param swipe_duration: 스크롤 지속 시간 (기본값 800ms)
    :return: True (요소 찾음) / False (최대 스크롤 후에도 요소 없음)
    """
    scroll_count = 0

    while scroll_count < max_scrolls:
        try:
            element = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((AppiumBy.ID, element_id))
            )
            if element.is_displayed():
                print(f"'{element_id}' 찾음 (스크롤 {scroll_count}회)")
                return True  # 요소를 찾으면 True 반환
        except Exception:
            print(f"'{element_id}' 찾지 못함... 스크롤 {scroll_count+1}/{max_scrolls} 실행")

        # 스크롤 실행
        scroll_screen(driver, direction, swipe_duration)
        scroll_count += 1

    print(f"{max_scrolls}회 스크롤 후에도 요소 '{element_id}' 찾지 못함")
    return False  # 요소를 찾지 못하면 False 반환

#바텀시트 스크롤
def scroll_in_bottomsheet_and_click(driver, resource_id, name_text):
    try:
        element = driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR, f'new UiScrollable(new Uiselector().resourceIdMatches(".*rv_contetns.*")).scrollIntoView(new Uiselector().resourceId("{resource_id}").textContains("{name_text}"))'
        )
        element.click()
        print(f"'{name_text}' 도매 선택")
    except Exception as e:
        print(f"'{name_text}' 도매 선택 실패: {e}")

#유동적인게 아닌 바텀시트 스크롤
def select_wholesaler_by_name(driver, name_text):
    try:
        selector = (
            'new UiScrollable(new UiSelector().resourceId("com.baropharm.app.dev:id/rv_contents"))'
            '.setAsVerticalList()'
            '.scrollIntoView(new UiSelector().resourceId("com.baropharm.app.dev:id/tv_wholesaler_name").textContains("'
            + name_text +
            '"))'
        )

        element = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((AppiumBy.ANDROID_UIAUTOMATOR, selector))
        )
        element.click()
        print(f"✅ '{name_text}' 도매상 클릭 완료")
    except Exception as e:
        print(f"❌ '{name_text}' 도매상 클릭 실패: {e}")


def scroll_screen(driver, direction="up", duration=800):
    """
    화면을 위 또는 아래로 스크롤하는 함수.

    :param driver: Appium WebDriver 인스턴스
    :param direction: 스크롤 방향 ("down" / "up")
    :param duration: 스크롤 지속 시간 (기본값 800ms)
    """
    window_size = driver.get_window_size()
    width = window_size["width"] // 2
    start_y = int(window_size["height"] * 0.8) if direction == "up" else int(window_size["height"] * 0.2)
    end_y = int(window_size["height"] * 0.3) if direction == "up" else int(window_size["height"] * 0.7)

    # ActionBuilder & PointerInput 사용하여 스크롤 수행
    actions = ActionBuilder(driver)
    pointer = PointerInput("touch", "finger")
    
    actions.w3c_actions.append(pointer.create_pointer_move(duration=0, x=width, y=start_y))
    actions.w3c_actions.append(pointer.create_pointer_down(button=PointerInput.TOUCH))
    actions.w3c_actions.append(pointer.create_pointer_move(duration=duration, x=width, y=end_y))
    actions.w3c_actions.append(pointer.create_pointer_up(button=PointerInput.TOUCH))
    
    driver.perform(actions)

def click_element_by_uiselector(driver, class_name, instance_index):
    """
    UiSelector를 이용하여 특정 클래스와 인덱스를 가진 요소를 클릭하는 함수.

    :param driver: Appium WebDriver 인스턴스
    :param class_name: 선택하려는 요소의 class 이름 (예: "android.view.ViewGroup")
    :param instance_index: 선택할 인스턴스 인덱스 (0부터 시작)
    """
    try:
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().className("{class_name}").instance({instance_index})'
            ))
        )
        element.click()
        print(f"요소 '{class_name}', 인스턴스 {instance_index} 클릭 완료")
    except Exception as e:
        print(f"Error clicking element with class '{class_name}' and instance {instance_index}: {e}")

def click_element_by_text(driver, text, timeout=20):
    """
    UIAutomator를 이용하여 특정 텍스트 값을 가진 요소를 클릭하는 함수.

    :param driver: Appium WebDriver 인스턴스
    :param text_value: 클릭하려는 요소의 text 값
    :param timeout: 최대 대기 시간 (기본값 10초)
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((AppiumBy.ANDROID_UIAUTOMATOR, f'new UiSelector().text("{text}")'))
        )
        element.click()
        print(f"요소 '{text}' 클릭 완료")
    except Exception as e:
        print(f"요소 '{text}' 찾기 실패: {e}")

def get_text_by_id(driver, element_id, timeout=10):
    """
    특정 ID 값을 가진 요소의 텍스트를 가져오는 함수.

    :param driver: Appium WebDriver 인스턴스
    :param element_id: 텍스트를 가져올 요소의 resource-id 값 (예: "com.baropharm.app.dev:id/tv_brand_name")
    :param timeout: 최대 대기 시간 (기본값: 10초)
    :return: 요소의 텍스트 (string) 또는 None
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((AppiumBy.ID, element_id))
        )
        text_value = element.text.strip()  # 텍스트 값 추출 및 앞뒤 공백 제거
        print(f"'{element_id}'에서 텍스트 추출: '{text_value}'")
        return text_value
    except Exception as e:
        print(f"요소 '{element_id}'에서 텍스트 추출 실패: {e}")
        return None

def enter_number_by_resource_id(driver, resource_id, index, number):
    """
    주어진 resource-id와 인덱스를 기준으로 해당 et_qty_editor에 숫자를 입력하는 함수.
    
    :param driver: Appium WebDriver 인스턴스
    :param resource_id: 입력할 et_qty_editor의 resource-id
    :param index: 입력할 et_qty_editor의 인덱스 (0부터 시작)
    :param number: 입력할 숫자
    """
    try:
        # resource-id와 인덱스를 이용해 UiSelector로 해당 요소를 찾기
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().resourceId("{resource_id}").instance({index})'
            ))
        )
        
        # 해당 요소가 로드된 후 텍스트 입력
        element.clear()  # 기존 텍스트 지우기
        element.send_keys(str(number))  # 숫자 입력
        print(f"'{index}' 번째 '{resource_id}'에 숫자 '{number}' 입력 완료")
    
    except Exception as e:
        print(f"'{resource_id}'에서 '{index}' 번째 요소에 숫자 입력 중 오류 발생: {e}")

def click_button_by_id(driver, element_id, retries=3):
    """
    주어진 id 값을 가진 요소를 클릭하는 함수. 재시도 로직이 포함되어 있습니다.
    """
    attempt = 0
    while attempt < retries:
        try:
            # 요소를 다시 찾음
            button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((AppiumBy.ID, element_id))
            )
            button.click()
            print(f"버튼 '{element_id}' 클릭 완료")
            time.sleep(2)  # 클릭 후에 잠시 대기하여 화면 전환을 기다립니다.
            return  # 성공적으로 클릭하면 함수 종료

        except Exception as e:
            if 'NoSuchElementException' in str(e):
                print(f"요소 '{element_id}'을 찾을 수 없습니다. 건너뜁니다.")
                break  # 요소가 없으면 종료
            elif 'StaleElementReferenceException' in str(e):
                print(f"Stale element reference exception occurred. Retrying... (Attempt {attempt + 1}/{retries})")
                time.sleep(1)  # 잠시 대기 후 재시도
            else:
                print(f"Error while clicking button '{element_id}': {e}")
                break  # 다른 예외 발생 시 루프 탈출

        attempt += 1
    print(f"Failed to click button '{element_id}' after {retries} attempts.")

def check_and_print_price(driver, element_id, label):
    try:
        price_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((AppiumBy.ID, element_id))
        )
        price = price_elem.text.strip()
        if price:
            print(f"{label} : {price}")
        else:
            print(f"{label} 금액 없음")
        time.sleep(1)
    except Exception as e:
        print(f"{label} 금액 없음 (에러: {e})")
        time.sleep(1)


def check_order_price_bottom(driver):
    check_and_print_price(
        driver,
        "com.baropharm.app.dev:id/tv_baropharm_total",
        "즉시결제"
    )
    check_and_print_price(
        driver,
        "com.baropharm.app.dev:id/tv_deferred_total",
        "후불결제"
    )
    check_and_print_price(
        driver,
        "com.baropharm.app.dev:id/tv_bnpl_total",
        "나중결제"
    )





#주문-------------------------------------------------------------------------------------------------------------------
proxies = {
    "http": "http://127.0.0.1:8080",
    "https": "http://127.0.0.1:8080",
}

#주문완료시 스크린샷 저장
def capture_screenshot(driver, screenshot_name="order_completion"):
    folder_path="./screenshots"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    #이름중복방지
    timestamp=time.strftime("%Y%m%d_%H%M%S")
    screenshot_path = f"{folder_path}/{screenshot_name}_{timestamp}.png"

    try:
        driver.save_screenshot(screenshot_path)
        print(f"스크린샷 저장 : {screenshot_path}")

    except Exception as e :
        print(f"저장 실패 : {e}")


def wait_for_text(driver, element_id, expected_text="주문 처리 완료", timeout=30, interval=3):
    """
    특정 ID 값을 가진 요소의 텍스트를 주기적으로 확인하며, 주문 상태를 체크하는 함수.
    - "주문 처리 완료"이면 성공
    - "주문 처리 중"이 아니면서 다른 상태가 나오면 PASS 처리

    :param driver: Appium WebDriver 인스턴스
    :param element_id: 텍스트를 가져올 요소의 resource-id 값
    :param expected_text: 대기할 최종 텍스트 값 (기본값: "주문 처리 완료")
    :param timeout: 최대 대기 시간 (초) (기본값: 30초)
    :param interval: 텍스트 확인 간격 (초) (기본값: 3초)
    :return: "완료" (주문 처리 완료) / "PASS" (다른 상태) / None (타임아웃)
    """
    start_time = time.time()  # 시작 시간 기록

    while time.time() - start_time < timeout:
        try:
            element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((AppiumBy.ID, element_id))
            )
            text_value = element.text.strip()  # 텍스트 추출 후 앞뒤 공백 제거

            print(f"현재 텍스트: '{text_value}' (기대값: '{expected_text}')")

            # ✅ 주문 처리 완료 → 성공
            if expected_text in text_value:
                print(f"텍스트 '{expected_text}' 확인 완료!")
                return "완료"

            # 🚨 주문 처리 중이면 계속 대기
            if "주문 처리 중" in text_value:
                print("⏳ '주문 처리 중' 상태 감지, 계속 대기...")
            else:
                # 주문 처리 중이 아니고 다른 상태라면 PASS 처리
                print(f"예상 외 상태 '{text_value}' 감지 → PASS 처리")
                return "PASS"

        except Exception as e:
            print(f"'{element_id}'에서 텍스트 확인 중 오류 발생: {e}")

        print(f"예상 텍스트가 나타날 때까지 대기 중... (최대 {timeout}초)")
        time.sleep(interval)  # 설정한 간격만큼 대기

    print(f"최대 {timeout}초 동안 '{expected_text}'를 찾지 못함")
    return None  # 타임아웃 발생 시 None 반환



#웹뷰----------------------------------------------------------------------------------------------------------------
# WebView 안에서 결제하기 및 확인 버튼을 클릭하는 함수
def perform_webview_actions(driver):
    if switch_to_webview(driver):  # WebView로 전환
        time.sleep(2)
        try:
            # WebView 안에서 결제하기 버튼을 클릭
            payment_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'pay-button')]"))
            )
            payment_button.click()
            print("결제하기 버튼 클릭 완료")
            time.sleep(3)  # 팝업이 나타나기 전 잠시 대기

            # 결제 완료 후 나타나는 팝업에서 확인 버튼 클릭
            confirm_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'custom-confirm-button')]"))
            )
            confirm_button.click()
            print("팝업 확인 버튼 클릭 완료")

        except Exception as e:
            print(f"Error while clicking payment or confirm button: {e}")
            driver.save_screenshot("error_in_webview.png")
            print(driver.page_source)
        finally:
            switch_to_native(driver)  # 작업 후 네이티브로 전환

# 네이티브 UI에서 추가 작업을 수행하는 함수
def perform_native_actions(driver):
    switch_to_native(driver)  # 네이티브로 전환
    try:
        # 네이티브 UI 요소 클릭 (예: 홈 버튼)
        home_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((AppiumBy.ID, "com.baropharm.app.dev:id/btn_move_to_home"))
        )
        home_button.click()
        print("Home 버튼 클릭 완료")
    except Exception as e:
        print(f"Home 버튼 클릭 중 오류 발생: {e}")

# WebView로 전환하는 함수
def switch_to_webview(driver):
    try:
        # 가능한 컨텍스트 목록을 가져옵니다.
        contexts = driver.contexts
        print(f"Available contexts: {contexts}")

        # WebView 컨텍스트를 찾습니다.
        for context in contexts:
            if 'WEBVIEW' in context:
                driver.switch_to.context(context)
                print(f"Switched to context: {context}")
                return True  # 성공 시 True 반환
        print("No WebView context found.")
        return False  # WebView 컨텍스트가 없을 경우 False 반환
    except Exception as e:
        print(f"Error during switching to WebView: {e}")
        return False

# 네이티브로 전환하는 함수
def switch_to_native(driver):
    try:
        driver.switch_to.context('NATIVE_APP')
        print("Switched to native context.")
    except Exception as e:
        print(f"Error while switching to native: {e}")



    

#------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.input
def test_login_success(driver):  
    """정상 로그인 케이스"""
    #handle_android_permissions(driver)
    system_noti_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "com.android.permissioncontroller:id/permission_allow_button"))
    )
    system_noti_button.click()

    email_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "com.baropharm.app.dev:id/et_email"))
    )
    email_field.send_keys("barocooper@nate.com")

    password_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "com.baropharm.app.dev:id/et_password"))
    )    
    password_field.send_keys("baro1234!")

    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "com.baropharm.app.dev:id/btn_sign_in"))
    )
    login_button.click()


    #click_button_by_id(driver, "com.baropharm.app.dev:id/btn_close")
    #time.sleep(2)
   
    popup_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "com.baropharm.app.dev:id/btn_close"))
    )
    popup_button.click()
    time.sleep(3)
    
    #get_access_token()
    #time.sleep(1)

    success_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/ll_search_view"))
    )

    assert success_element.is_displayed(), "로그인 실패!"
    print("로그인 성공!")

def test_payment(driver):
    click_button_by_id(driver, "com.baropharm.app.dev:id/iv_cart")
    print("장바구니 진입")
    time.sleep(3)

    click_button_by_id(driver, "com.baropharm.app.dev:id/btn_expand")
    print("주문내역 펼침")
    time.sleep(3)

    check_order_price_bottom(driver)
            
    click_button_by_id(driver, "com.baropharm.app.dev:id/btn_request_order")
    print("주문하기 진입")
    time.sleep(5)

    perform_webview_actions(driver)
    print("윕뷰 예치금으로 결제 진행")
    time.sleep(3)
    
    result = wait_for_text(driver, "com.baropharm.app.dev:id/tv_ordered_message")
    if result == "완료":
        print("주문 완료")
    elif result == "PASS":
        print("일부 도매 실패, 주문실패")
    else:
        print("주문처리중 실패")
    time.sleep(1)

    capture_screenshot(driver, "order_completion")
    print("결제완료 후 스크린샷 저장")
    time.sleep(2)
       
    click_button_by_id(driver, "com.baropharm.app.dev:id/btn_move_to_order_history")
    print("통합주문내역으로 이동")
    time.sleep(3)    

    click_button_by_id(driver, "com.baropharm.app.dev:id/iv_right_menu_1")
    print("홈으로 이동")
    time.sleep(5)

@pytest.mark.input
def test_community_check(driver):

    into_community = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/layout_community"))
    )
    into_community.click()

    time.sleep(3)

    check_community = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "com.baropharm.app.dev:id/iv_home"))
    )
    assert check_community.is_displayed(), "커뮤니티 진입 실패"
    print("커뮤니티 진입 확인")
    
    time.sleep(2)

    go_to_home = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/layout_home"))
    )
    go_to_home.click()

    success_element = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "com.baropharm.app.dev:id/iv_baropharm"))
    )

    assert success_element.is_displayed(), "커뮤티 진입 실패!"
    print("커뮤니티 진입 체크")
@pytest.mark.input
def test_brand_check_flow(driver):
    #scroll_to_element_by_partial_text(driver, "프리미엄 제약 브랜드관")

    time.sleep(3)

    click_brand_ui = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((AppiumBy.ANDROID_UIAUTOMATOR, 
                                    'new UiSelector().resourceId("com.baropharm.app.dev:id/btn_view_all").instance(1)'))
    )
    click_brand_ui.click()
    
    check_brand_logo = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/iv_thumbnail"))
    )
    assert check_brand_logo.is_displayed(), "브랜드관 로고 확인 실패"
    print("브랜드관 노출 확인")
    time.sleep(2)


    #click_element_by_uiselector(driver, "android.view.ViewGroup", 5)
    click_element_by_text(driver, "쿠퍼의제품세상")
    print("쿠퍼의제품세상 선택")
    
    click_button_by_id(driver, "com.baropharm.app.dev:id/btn_close")
    time.sleep(3)

    get_text_by_id(driver, "com.baropharm.app.dev:id/tv_brand_name")
    check_brand_name = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/tv_brand_name"))
    )
    assert check_brand_name.is_displayed(), "브랜드명 확인 실패"
    print("브랜드명 확인 완료")
    time.sleep(2)

    go_to_home = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/iv_right_menu_2"))
    )
    go_to_home.click()
    time.sleep(1)


def test_switching_store(driver):
    click_element_by_text(driver, "스토어")
    time.sleep(3)

    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/tv_search_placeholder"))
    )

    hint_text = element.text.strip()
    expected_text = "바로팜 스토어 오픈!!!?"

    assert hint_text == expected_text, f"텍스트 불일치 : 기대='{expected_text}', 실제='{hint_text}'"
    print("스토어 진입 성공")

@pytest.mark.search
def test_search_flow(driver):
    click_search = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((AppiumBy.ID, "com.baropharm.app.dev:id/ll_search_view"))
    )
    click_search.click()
    print("메인홈 > 검색란 선택")
    time.sleep(1)

    input_search = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/et_search"))
    )
    assert input_search.send_keys("쿠퍼"), "입력 실패"
    print("검색어 읿력 성공")

    click_enter_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((AppiumBy.ID, "com.baropharm.app.dev:id/iv_search"))
    )
    click_enter_btn.click()
    time.sleep(1)

    check_success_search = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/sw_out_of_stock"))
    )
    assert check_success_search.is_displayed(), "검색실패"
    print("검색 성공")
 
@pytest.mark.search
def test_input_cart(driver):


    scroll_to_element_by_partial_text(driver, "쿠퍼_전문의약품")
    time.sleep(1)

    click_element_by_text(driver, "쿠퍼_전문의약품")
    time.sleep(1)

    capture_screenshot(driver, "search")
    time.sleep(1)

    check_inventory = WebDriverWait(driver,10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/et_qty_editor"))
    )
    assert check_inventory.is_displayed(), "주문상세 진입 실패"
    print("주문상세 진입")
    time.sleep(1)

    enter_number_by_resource_id(driver, "com.baropharm.app.dev:id/et_qty_editor", 0, 10)
    print("상품 추가")
    time.sleep(3)

    click_add_cart = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/btn_add_cart"))
    )
    click_add_cart.click()
    time.sleep(2)

    click_button_by_id(driver, "com.baropharm.app.dev:id/btn_positive")
    print("중복 장바구니 있는경우 확인")
    time.sleep(3)

    click_go_to_search = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/btn_go_to_search"))
    )
    click_go_to_search.click()
    time.sleep(1)

    click_recent = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((AppiumBy.ID, "com.baropharm.app.dev:id/ll_recent_keyword"))
    )
    click_recent.click()
    time.sleep(1)

    click_element_by_text(driver, "쿠퍼 OTC")
    time.sleep(1)

    assert check_inventory.is_displayed(), "주문상세 진입 실패"
    print("주문상세 진입")
    time.sleep(1)

    enter_number_by_resource_id(driver, "com.baropharm.app.dev:id/et_qty_editor", 2, 10)
    print("상품 추가")
    time.sleep(3)
    
    click_add_cart = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/btn_add_cart"))
    )
    click_add_cart.click()
    time.sleep(2)

    click_button_by_id(driver, "com.baropharm.app.dev:id/btn_positive")
    print("중복 장바구니 있는경우 확인")
    time.sleep(3)

    click_go_to_search = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/btn_go_to_search"))
    )
    click_go_to_search.click()
    time.sleep(1)

    click_recent = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((AppiumBy.ID, "com.baropharm.app.dev:id/ll_recent_keyword"))
    )
    click_recent.click()
    time.sleep(1)



    click_element_by_text(driver, "쿠퍼_제품TTeessTt")
    time.sleep(1)


    click_element_by_uiselector(driver, "android.view.ViewGroup", 5)
    print("최근 검색어 선택")
    time.sleep(2)

    click_add_cart = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/btn_add_cart"))
    )
    click_add_cart.click()
    time.sleep(2)

    click_button_by_id(driver, "com.baropharm.app.dev:id/btn_positive")
    print("중복 장바구니 있는경우 확인")
    time.sleep(3)

    click_go_to_cart = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/btn_go_to_cart"))
    )
    click_go_to_cart.click()
    print("바텀시트 > 장바구니 선택")
    time.sleep(1)

@pytest.mark.input
def test_search_inventory(driver):
    click_cartitem = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/iv_cart"))
    )
    click_cartitem.click()
    time.sleep(4)

    find_number = driver.find_elements(AppiumBy.ID, "com.baropharm.app.dev:id/btn_all_wholesaler_products")
    print(f"btn : {len(find_number)}")

    if len(find_number) >= 1:
        find_number[0].click()
        time.sleep(2)

    success_element = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/tv_wholesaler_name"))
    )
    
    assert success_element.is_displayed(), "전체 상품 보기 진입 실패"
    wholesaler_name = success_element.text.strip()
    print(f"{wholesaler_name}의 도매 진입 성공")
    time.sleep(1)

    change_wholesaler = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ID, "com.baropharm.app.dev:id/btn_select_wholesaler"))
    )
    change_wholesaler.click()
    print("도매변경버튼 선택")
    time.sleep(3)

    select_wholesaler_by_name(driver, "쥬디_의약품")
    time.sleep(10)

    


    
    












    
    

    
    

    
    