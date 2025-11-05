from operator import truediv

import pytest
import requests
from selenium import webdriver
from selenium.common import TimeoutException, ElementClickInterceptedException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import urllib.parse
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import json
import os
import time
import re



## 테스트 시나리오
"""검색 > 장바구니 추가 > 주문창에서 좌측 판매금액 + 금융할인 + 주문금액 각각 더한 후 우측 결제정보에서 금액 체크
백오피스에서 order쏴서 받는 금액들 세팅값과 2차 검증 진행"""

BASE_URL = "https://www.dev.barodev.com"
CMS_URL = "https://cms.dev.barodev.com"
API_URL = "https://api-v2.dev.barodev.com"

"""공통 컾포넌트"""

def click_element_by_class(driver, class_name: str, index: int):
    try:
        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, class_name))
        )
        if len(elements) > index:
            elements[index].click()
            print(f"클래스 '{class_name}', 인덱스 {index} 클릭완료")
        else :
            print(f"클래스 '{class_name}', 인덱스 {index} 보다 적음")

    except Exception as e:
        print(f"Error clicking element with class '{class_name}' and instance {index}: {e}")

def search_directly_by_url(driver, keyword):
    encoded_keword = urllib.parse.quote(keyword)
    search_url = f"{BASE_URL}/order?q={encoded_keword}"
    driver.get(search_url)
    time.sleep(3)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "item-product"))
        )
        print(f"\n'{keyword}' 검색 결과 페이지 로딩 성공")
    except Exception as e:
        print(f"검색 결과 로딩 실패: {e}")


def click_product_by_name(driver, product_name):
    try:
        product_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f'//li[contains(@class, "item-product")]//span[contains(text(), "{product_name}")]/ancestor::li'))
        )
        product_element.click()
        print(f"'{product_name}' 클릭")

    except Exception as e:
        print(f"'{product_name}' 실패: {e}")

def input_inventory_unit(driver, inventory_unit, number):
    try:
        inventory_unit_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, f"inventory__{inventory_unit}"))
        )
        inventory_unit_element.send_keys(str(number) + Keys.ENTER)
        print(f"'{inventory_unit}' 재고아이디 입력")

    except Exception as e:
        print(f"'{inventory_unit}' 재고아이디 입력 실패: {e}")

def confirm_already_cartitem_btn(driver):
    try:
        confirm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swal2-confirm"))
        )
        confirm_btn.click()
        print("장바구니에 이미 있는 팝업 사용")
        time.sleep(3)

    except Exception as e:
        print("장바구니 이미 있는상품 처리 완료")

def suppresstoday_guard(driver):
    try:
        close_today_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'label[for="HIDE_TODAY"]'))
        )
        close_today_btn.click()
        time.sleep(3)        

        close_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.close-button'))
        )
        close_btn.click()        
        print("\n함께배송 오늘하루 보지않기 노출 확인 및 오늘하루보지않기 선택")
        time.sleep(3)

        click_order_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "baropharmOrder"))
        )
        click_order_btn.click()
        time.sleep(3)

    except Exception as e:
        print("함께배송 오늘하루 보지않기 팝업 미노출")

def select_card_brand(driver, card_name, timeout=10, attempts=3):
    """
        결제수단 영역의 카드 브랜드 드롭다운에서 `card_name`을 선택합니다.
        1) card-list 안의 트리거 버튼(.txt-limit)을 클릭
        2) 포탈로 생성되는 select-list-wrap 내부에서 옵션 버튼 클릭
        3) 트리거 텍스트가 card_name으로 바뀌었는지 검증
        """
    for attempt in range(1, attempts + 1):
        try:
            # 1) 트리거(현재 선택된 카드 표시 버튼) 클릭
            trigger = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "div.card-list .select-values button.txt-limit")
                )
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", trigger)
            ActionChains(driver).move_to_element(trigger).click().perform()

            # 2) 드롭다운 옵션 대기 후 '국민카드' 클릭
            option = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located(
                    (By.XPATH,
                     f'//div[contains(@class,"select-list-wrap") and contains(@class,"small")]'
                     f'//ol[contains(@class,"select-list")]'
                     f'//button[normalize-space()="{card_name}"]')
                )
            )
            # 스크롤 + 액션체인 클릭
            driver.execute_script("arguments[0].scrollIntoView({block:'nearest'});", option)
            ActionChains(driver).move_to_element(option).pause(0.05).click().perform()

            # 3) 트리거 텍스트가 실제로 card_name으로 바뀌었는지 검증
            WebDriverWait(driver, timeout).until(
                lambda d: card_name in d.find_element(
                    By.CSS_SELECTOR, "div.card-list .select-values button.txt-limit"
                ).text
            )
            print(f"카드 선택 성공: {card_name} (시도 {attempt}회)")
            time.sleep(3)
            return
        except (TimeoutException, StaleElementReferenceException) as e:
            print(f"⚠️ 재시도 필요(시도 {attempt}회): {type(e).__name__}")
            # 드롭다운이 닫힌 상태일 수 있으니 다음 루프에서 다시 트리거를 열도록 함
            continue

    raise AssertionError(f"카드 선택 실패: {card_name}")


def muliple_order_close(driver):
    try:
        muliple_order_close_ele = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'span.icon-x'))
        )
        muliple_order_close_ele.click()
        print("다빈도주문 탭 노출")
        time.sleep(3)

    except Exception as e:
        print("다빈도주문 탭 미노출")

#예치금 초기화때 사용
def deposit_to_one(driver):
    input_box = driver.find_elements(By.CSS_SELECTOR, "input.input-box.small[type='search']")
    input_box[1].clear()
    input_box[1].send_keys("100")
    assert input_box[1].text == "", "예치금 초기화 실패"
    print("예치금 100원 세팅 성공")
    time.sleep(3)


def deposit_to_zero_check(driver):
    input_box = driver.find_elements(By.CSS_SELECTOR, "input.input-box.small[type='search']")
    price = input_box[1].get_attribute("value")
    input_box[1].clear()
    assert input_box[1].text == "", "예치금 초기화 실패"
    print("예치금 초기화 성공")
    time.sleep(3)

    input_box[1].send_keys(f"{price}")

    deposit = input_box[1].get_attribute("value")
    print(f"예치금 확인용 : {deposit}")
    time.sleep(3)
    assert int(deposit.replace(",", "")) > 0, "예치금 전액 입력 실패"
    print("예치금 전액 입력 성공")


#캡쳐용
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

def wait_for_order_complete(driver, max_retries: int =20, delay : int =1):
    #주문완료 메시지 노출까지 기다림
    for attempt in range(max_retries):
        try:
            elem = WebDriverWait(driver, delay).until(
                EC.visibility_of_element_located((
                    By.XPATH,
                    '//div[contains(@class, "wrapper-state")]'
                    '//div[contains(@class, "success") and contains(., "주문이") and contains(., "완료")]'
                ))
            )
            if elem and "완료" in elem.text:
                print(f"\n주문완료 메시지 확인 : {elem.text}")
                capture_screenshot(driver)
                return True
        except TimeoutException:
            print(f"\n{attempt+1}/{max_retries} 주문 생성중...")
            continue
    print("주문실패")
    capture_screenshot(driver)
    return False

def as_int(s: str) -> int:
    # "59,994원", "-36", "  1,964 " 등에서 숫자만 추출
    #import re
    m = re.findall(r"-?\d+", s.replace(",", ""))
    return int("".join(m)) if m else 0


"""CMS 예치금 사용 후 충전용 API"""
def cms_token_get():
    url = f"{CMS_URL}/api/login"
    payload = {
        "username": "cooper", "password": "baro1234!"
    }
    headers = {
        "Content-Type": "application/json;charset=UTF-8"
    }
    response = requests.post(url, headers=headers, json=payload)
    """   로그인 안될때 디버깅용
    print("응답 코드:", response.status_code)
    print("응답 헤더:", response.headers)
    print("응답 Body:", response.text[:500])
    """
    assert response.status_code == 200, f"CMS login fail : {response.status_code}"
    print("CMS login success")
    return response.json()["access"]

def charge_deposit(token):
    url = f"{API_URL}/deposit-histories"
    payload = {
        "amount": 15914451,
        "type": "기타",
        "user_id": "20909",
        "deposit_type": "deposit",
        "content": "test"
    }
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Authorization": f"Baro {token}"
    }
    response = requests.post(url, headers=headers, json=payload)
    assert response.status_code in (200, 201, 202, 203), f"예치금 충전 실패 : {response.status_code}"
    print("예치금 충전 성공")
    return response.json()

def payment_benefits_switch_mode(token, value_benefit):
    print(f"받은 액티브값 : {value_benefit}")
    url = f"{API_URL}/payment-benefits/161/active"
    payload = {
        "is_active":value_benefit
    }
    print(f"payload value: {payload}")
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Authorization": f"Baro {token}"
    }
    response = requests.patch(url, headers=headers, json=payload)
    assert response.status_code in (200, 201, 202, 203, 204), f"결졔 혜택 변경 실패 : {response.status_code}"
    print(f"결제 혜택 변경 성공 {value_benefit}")   #로그 확인용 CMS배포시 에러나는 경우 대비용

    if response.status_code == 204:
        return True
    return response.json()

def confirm_cancel_api(token, order_no):
    url = f"{API_URL}/orders/{order_no}"
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Authorization": f"Baro {token}"
    }
    response = requests.get(url, headers=headers)
    assert response.status_code == 200, f"실패 응답값 : {response.status_code}"
    print("조회 성공")

    status_code = response.json()["status"]
    print(f"status_code: {status_code}")
    assert "CANCELLED" == status_code, "취소아님"





@pytest.fixture(scope="session")
#크롬 브라우저 실행
def driver():
    options = Options()
    options.add_argument("--window-size=1920,1920")
    #service = Service("/usr/local/bin/chromedriver")
    #options.add_argument("--window-size=maximized")
    #options.add_argument("--headless")    #브라우저 실행 없이 실행하는 옵션
    #options.headless = True

    driver = webdriver.Chrome(options=options)
    driver.get(BASE_URL)
    yield driver
    driver.quit()

#테스트 항목(이전 test_ 항목)
def login(driver):

    login_id = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "userId"))
    )
    login_id.send_keys("barocooper@nate.com")
    time.sleep(1)

    login_pw = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "userPwd"))
    )
    login_pw.send_keys("baro1234!")
    time.sleep(1)

    click_enter_btn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//span[text()="로그인"]/ancestor::button'))
    )
    click_enter_btn.click()
    time.sleep(2)

    element = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, '//em[text()="약국"]'))
    )
    assert element.text == "약국", "로그인 실패"
    print("로그인 성공")
    time.sleep(3)


def add_products_cartitems(driver):

    click_order_tab = WebDriverWait(driver, 10).until(
        EC. element_to_be_clickable((By.XPATH, '//img[@alt="주문하기"]/parent::a'))
    )
    click_order_tab.click()
    time.sleep(3)
    assert "/order" in driver.current_url, "주문하기 진입 실패"
    print("\n주문하기 진입 성공")

    #다빈도주문 방어
    muliple_order_close(driver)


    search_directly_by_url(driver, "쿠퍼")
    time.sleep(3)

    click_product_by_name(driver, "쿠퍼 QUASIDRUG")
    time.sleep(2)

    input_inventory_unit(driver, "4129283", 10)
    print("의약외품 장바구니 추가")
    time.sleep(2)

    confirm_already_cartitem_btn(driver)
    time.sleep(2)

    click_product_by_name(driver, "쿠퍼 ETC")
    print("제품도매 일반의약품 장바구니 추가")
    time.sleep(3)

    input_inventory_unit(driver, "4129487", 10)
    time.sleep(3)

    confirm_already_cartitem_btn(driver)
    time.sleep(2)

    click_product_by_name(driver, "쿠퍼_리뷰가 많은 상품")
    print("제품상품 장바구니 추가")
    time.sleep(3)

    input_inventory_unit(driver, "4129492", 10)
    time.sleep(2)

    confirm_already_cartitem_btn(driver)
    time.sleep(3)

    click_product_by_name(driver, "쿠퍼_로수반정(병) 10mg 28T_520원")
    print("의약품도매 상품 장바구니 추가")
    time.sleep(3)

    input_inventory_unit(driver, "4129447", 10)
    time.sleep(2)

    confirm_already_cartitem_btn(driver)
    time.sleep(3)

def wait_for_payment_popup(driver):
    click_order_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "baropharmOrder"))
    )
    click_order_btn.click()
    time.sleep(3)

    suppresstoday_guard(driver)  # 함께배송 방어

    check_order_popup = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, '//h4[contains(text(), "바로팜몰 결제내역")]'))
    )
    assert "바로팜몰 결제내역" in check_order_popup.text
    print(f"바로팜몰 진입  문구 확인 : {check_order_popup.text}")


def bc_card_warning_text(driver):
    #확인필요함 경고문구 확인용
    check_warning_text_for_bc = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'span.card-exception-text'))
    )
    assert check_warning_text_for_bc.text == "*전용카드의 경우 무이자할부 적용 예외 될 수 있음.", "BC카드 5만원이상 경고문구 노출 실패"
    print("BC카드 5만원이상 경고문구 노출")




def pt01_deposit_pay(driver):

    #결제창 대기 div.payment-layer-wrap : 결제창
    layer = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'div.payment-layer-wrap'))
    )
    assert layer.is_displayed(), "결제창 미노출"
    print("결제창 노출 성공")

    # 섹션 컨테이너 먼저 잡고
    container = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.product-table-list"))
    )

    #li들 가져오기
    section_list = container.find_elements(By.CSS_SELECTOR, ":scope > li")  # 또는 "ul.product-table-list > li"

    total_sale_sum = 0                  #판매금액
    total_fin_disscout_sum = 0          #할인금액
    total_order_sum = 0                 #주믄금액

    for sec in section_list:
        tbodies = sec.find_elements(By.CSS_SELECTOR, "div.custom-table .custom-table-body table tbody")
        if not tbodies:
            continue

        rows = tbodies[0].find_elements(By.TAG_NAME, "tr")
        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            if len(tds) == 5:
                product_name = tds[0].text.strip()
                qty = as_int(tds[1].text)
                sale_amount = as_int(tds[2].text)
                fin_discount = as_int(tds[3].text)
                order_amount = as_int(tds[4].text)


                print(f"상품명 = {product_name}\n 수량 = {qty}, 판매금액 = {sale_amount}   할인금액 = {fin_discount}, 주문금액 = {order_amount}")

                assert product_name != ""

                total_sale_sum += sale_amount
                total_fin_disscout_sum += fin_discount
                total_order_sum += order_amount

    print(f" 합계금액\n판매금액 = {total_sale_sum} | 할인금액(쿠폰,금융) = {total_fin_disscout_sum} | 주문금액 = {total_order_sum}")
    #여기까지 묶을것임

    #우측 결제정보 영역
    #판매금액
    sale_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((
            By.XPATH,
            #li 안에 "판매금액" 텍스트가 있고 같은 li 내 strong.price-txt 찾음
            '//li[.//p[contains(text(), "판매금액")]]//strong[contains(@class, "price-txt")]'
        ))
    )
    right_sale_total = as_int(sale_elem.text)

    # 할인을 금융할인과 할인쿠폰 두개로 설정
    finance_discount_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((
            By.XPATH,
            '(//li[.//p[contains(text(),"금융할인")]]//strong | //li[.//p[contains(text(),"금융할인")]]//span)[last()]'
        ))
    )
    right_finance_discount_total = as_int(finance_discount_elem.text)

    coupon_discount_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((
            By.XPATH,
            '(//p[contains(@class,"coupon-box")]'
            '//span[contains(normalize-space(.),"할인쿠폰")]'
            '/ancestor::*[self::li or self::div][1]'
            '//div[contains(@class,"amount-box")]'
            '//*[self::strong or self::span])[last()]'
        ))
    )
    right_coupon_discount_total = as_int(coupon_discount_elem.text)

    right_discount_total = right_finance_discount_total + right_coupon_discount_total

    #카드 결제금액 : 결제금액 노출할대 확인시켜주는 용도로 사용
    total_amount_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((
            By.XPATH,
            '(//li[.//p[contains(text(),"카드 결제액")]]//strong | //li[.//p[contains(text(),"카드 결제액")]]//span)[last()]'
        ))
    )
    total_amount_elem = as_int(total_amount_elem.text)

    right_total_sale_amount = right_sale_total - right_discount_total

    #포인트, 예치금 금액 확인용
    input_boxes = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input.input-box.small[type='search']"))
    )
    points = as_int(input_boxes[0].get_attribute("value"))
    deposit = as_int(input_boxes[1].get_attribute("value"))

    print(f"우측 판매금액 : {right_sale_total}, 우측 할인금액 : {right_discount_total}, 결제금액 : {right_total_sale_amount}")
    assert total_fin_disscout_sum == right_discount_total, "할인금액 불일치"
    print(f"할인금액 일치 : {total_fin_disscout_sum}")
    #discount_right_price = int(right_total_sale_amount * 0.993) >> 카드혜택시에만 적용으로 해제
    assert total_order_sum == right_total_sale_amount, "좌측 도매금액과 우측 결제금액 총합 불일치"
    print(f"\n도매영역 판매금액 : {total_order_sum}, 결제영역 판매금액 : {right_total_sale_amount}\n도매영역 할인금액 : {total_fin_disscout_sum}, 결제 영역 할인 금액 : {right_discount_total}")
    print(f"\n카드 결제 금액 : {total_amount_elem}, 포인트 결제 금액 : {points}, 예치금 결제 금액 : {deposit}")
    time.sleep(5)

def pt01_card_benefit_pay(driver):


    #결제창 대기 div.payment-layer-wrap : 결제창
    layer = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, 'div.payment-layer-wrap'))
    )
    assert layer.is_displayed(), "결제창 미노출"
    print("결제창 노출 성공")

    # 섹션 컨테이너 먼저 잡고
    container = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.product-table-list"))
    )

    #li들 가져오기
    section_list = container.find_elements(By.CSS_SELECTOR, ":scope > li")  # 또는 "ul.product-table-list > li"

    total_sale_sum = 0                  #판매금액
    total_fin_disscout_sum = 0          #할인금액
    total_order_sum = 0                 #주믄금액

    for sec in section_list:
        tbodies = sec.find_elements(By.CSS_SELECTOR, "div.custom-table .custom-table-body table tbody")
        if not tbodies:
            continue

        rows = tbodies[0].find_elements(By.TAG_NAME, "tr")
        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
            if len(tds) == 5:
                product_name = tds[0].text.strip()
                qty = as_int(tds[1].text)
                sale_amount = as_int(tds[2].text)
                fin_discount = as_int(tds[3].text)
                order_amount = as_int(tds[4].text)


                print(f"상품명 = {product_name}\n 수량 = {qty}, 판매금액 = {sale_amount}   할인금액 = {fin_discount}, 주문금액 = {order_amount}")

                assert product_name != ""

                total_sale_sum += sale_amount
                total_fin_disscout_sum += fin_discount
                total_order_sum += order_amount

    print(f" 합계금액\n판매금액 = {total_sale_sum} | 할인금액(쿠폰,금융) = {total_fin_disscout_sum} | 주문금액 = {total_order_sum}")
    #여기까지 묶을것임

    #우측 결제정보 영역
    #판매금액
    sale_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((
            By.XPATH,
            #li 안에 "판매금액" 텍스트가 있고 같은 li 내 strong.price-txt 찾음
            '//li[.//p[contains(text(), "판매금액")]]//strong[contains(@class, "price-txt")]'
        ))
    )
    right_sale_total = as_int(sale_elem.text)

    # 할인을 금융할인과 할인쿠폰 두개로 설정
    finance_discount_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((
            By.XPATH,
            '(//li[.//p[contains(text(),"금융할인")]]//strong | //li[.//p[contains(text(),"금융할인")]]//span)[last()]'
        ))
    )
    right_finance_discount_total = as_int(finance_discount_elem.text)

    coupon_discount_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((
            By.XPATH,
            '(//p[contains(@class,"coupon-box")]'
            '//span[contains(normalize-space(.),"할인쿠폰")]'
            '/ancestor::*[self::li or self::div][1]'
            '//div[contains(@class,"amount-box")]'
            '//*[self::strong or self::span])[last()]'
        ))
    )
    right_coupon_discount_total = as_int(coupon_discount_elem.text)



    right_discount_total = right_finance_discount_total + right_coupon_discount_total

    #카드 결제금액 : 결제금액 노출할대 확인시켜주는 용도로 사용
    total_amount_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((
            By.XPATH,
            '(//li[.//p[contains(text(),"카드 결제액")]]//strong | //li[.//p[contains(text(),"카드 결제액")]]//span)[last()]'
        ))
    )
    total_amount_elem = as_int(total_amount_elem.text)

    right_total_sale_amount = (right_sale_total - right_discount_total)

    #포인트, 예치금 금액 확인용
    input_boxes = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input.input-box.small[type='search']"))
    )
    points = as_int(input_boxes[0].get_attribute("value"))
    deposit = as_int(input_boxes[1].get_attribute("value"))

    #결제혜택 적용
    card_discount = (right_total_sale_amount * 7) // 1000
    discount_right_price = right_finance_discount_total + right_coupon_discount_total + card_discount
    ptbenefit_total_fin_disscout_sum = total_fin_disscout_sum + card_discount

    #우측 맞누는 작업
    ptbenefit_total_order_sum = total_order_sum - card_discount
    discount_right_total_sale_price = right_total_sale_amount - card_discount

    print(f"우측 판매금액 : {right_sale_total}, 우측 할인금액 : {right_discount_total}, 결제금액 : {right_total_sale_amount}")
    assert ptbenefit_total_fin_disscout_sum == discount_right_price, "할인금액 불일치"  #이슈나는 이유 좌측 금융, 쿠폰 할인 합과 우측 금융할인 할인쿠폰에 카드할인이 더해지는데 카드값이 추가안됨
    print(f"할인금액 일치 : {total_fin_disscout_sum}")
    assert ptbenefit_total_order_sum == discount_right_total_sale_price, "좌측 도매금액과 우측 결제금액 총합 불일치"
    print(f"\n도매영역 판매금액 : {total_order_sum}, 결제영역 판매금액 : {right_total_sale_amount}\n도매영역 할인금액 : {total_fin_disscout_sum}, 결제 영역 할인 금액 : {right_discount_total}")
    print(f"\n카드 결제 금액 : {total_amount_elem}, 포인트 결제 금액 : {points}, 예치금 결제 금액 : {deposit}")
    time.sleep(5)





def deposit_payment(driver):

    pay_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(), "결제하기")]]'))
    )
    pay_btn.click()
    time.sleep(3)

    ok_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.swal2-confirm.swal2-styled'))
    )
    ok_btn.click()
    time.sleep(10)

    assert wait_for_order_complete(driver), "결제 실패"
    print("결제 성공")
    time.sleep(3)

    home_btn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.baropharm-logo"))
    )
    home_btn.click()
    time.sleep(1)

def card_benefit_payment(driver):

    pay_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(), "결제하기")]]'))
    )
    pay_btn.click()
    time.sleep(3)

    ok_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.swal2-confirm.swal2-styled'))
    )
    ok_btn.click()
    time.sleep(10)

    assert wait_for_order_complete(driver), "결제 실패"
    print("카드 결제 성공")
    time.sleep(3)

    home_btn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.baropharm-logo"))
    )
    home_btn.click()
    time.sleep(1)

def go_to_orders(driver):
    order_management_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "주문관리")]/parent::a'))
    )
    ActionChains(driver).move_to_element(order_management_btn).perform()
    time.sleep(1)

    orders_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "통합주문내역")]/parent::p'))
    )
    orders_btn.click()
    time.sleep(3)

    assert "/order/history" in driver.current_url, "통합주문내역 진입 실패"
    print("통합주문내역 진입 성공")

def order_history_list(driver):
    order_lists = driver.find_elements(By.CSS_SELECTOR, "div.custom-table-body table tbody tr")

    results = []
    for order_list in order_lists:
        tds = order_list.find_elements(By.CSS_SELECTOR, "td")

        order_date = tds[0].text.strip()    #주문일시
        order_no = tds[1].text.strip()      #주분번호
        wholesaler = tds[3].text.strip()    #판매처
        product_name = tds[4].text.strip()  #상품명
        qty = tds[5].text.strip()           #주문수량
        cancel_qty = tds[6].text.strip()    #취소수량
        amount = tds[7].text.strip()        #주문금액

        order_data = {
            "주문일시": order_date,
            "주문번호": order_no,
            "판매처명": wholesaler,
            "상품명": product_name,
            "주문수량": qty,
            "취소수량": cancel_qty,
            "판매금액": amount
        }

        print(
            f"\n[주문내역] "
            f"(주문일시: {order_date}), "
            f"(주문번호: {order_no}), "
            f"(판매처명: {wholesaler}), "
            f"(상품명: {product_name}), "
            f"(주문수량: {qty}), "
            f"(취소수량: {cancel_qty}), "
            f"(판매금액: {amount})"
        )
        results.append(order_data)


def order_desc_cancel(driver):
    click_first_order = driver.find_elements(By.CSS_SELECTOR, "div.custom-table-body table tbody tr")
    click_first_order[0].click()
    time.sleep(3)


    order_url = driver.current_url
    assert "/order/history/detail" in order_url, "주문상세 진입 실패"
    print(f"주문상세 진입 성공 : {order_url}")

    cancel_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.cancel-btn-box'))
    )
    cancel_btn.click()
    time.sleep(3)

    cancel_agree_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "취소하기")]/parent::div'))
    )
    cancel_agree_btn.click()
    time.sleep(3)

    cancel_complete_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "확인")]/parent::div'))
    )
    cancel_complete_btn.click()
    time.sleep(3)

    check_cancel = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.history-table-info p.cancel"))
    )
    print(f"취소 상태 텍스트: {check_cancel.text}")
    assert "주문취소" in check_cancel.text, "주문취소 문구 미노출"

    order_no = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.history-table-info span:nth-of-type(2)"))
    )
    print(f"주문 번호 : {order_no.text}")

    order_no_int = int(order_no.text)
    token = cms_token_get()
    confirm_cancel_api(token, f'{order_no_int}')


def charge_deposit_success(driver):

    token = cms_token_get()
    charge = charge_deposit(token)
    assert charge is not None
    time.sleep(3)


def switch_payment_benefit_on(driver):

    token = cms_token_get()
    switch = payment_benefits_switch_mode(token, True)

    print("결제혜택 ON, 국민카드")
    assert switch is True
    time.sleep(3)

def switch_payment_benefit_off(driver):

    token = cms_token_get()
    switch = payment_benefits_switch_mode(token, False)

    print("결제혜택 off, 국민카드")
    assert switch is True
    time.sleep(3)



def test_full_payment_auto_test(driver):
    #로그인
    login(driver)
    #상품 검색 및 장바구니 추가
    add_products_cartitems(driver)
    #결제팝업
    wait_for_payment_popup(driver)
    #결제창 금액 체크
    pt01_deposit_pay(driver)
    #예치금확인
    deposit_to_zero_check(driver)
    #결제 완료
    deposit_payment(driver)
    #사용한 예치금 충전
    charge_deposit_success(driver)
    #상품 검색 및 장바구니 상품 추가 (재진입)
    add_products_cartitems(driver)
    #결제혜택 on (결제혜택 기간에 포함되어야 카드 금액이 디폴트로 세팅됨
    switch_payment_benefit_on(driver)
    #결제 팝업
    wait_for_payment_popup(driver)
    #카드결제금액 세팅
    deposit_to_one(driver)
    #bc카드 문구 확인
    bc_card_warning_text(driver)
    #카드 변경
    select_card_brand(driver, "국민카드")
    #9.결제창 금액 체크
    pt01_card_benefit_pay(driver)
    #10.결제 진행
    card_benefit_payment(driver)
    #결제혜택 off
    switch_payment_benefit_off(driver)
    #통합주문내역 진입
    go_to_orders(driver)
    #통합주문내역 리스트
    order_history_list(driver)
    #주문취소 확인
    order_desc_cancel(driver)
























