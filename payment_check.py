from operator import truediv

import pytest
import requests
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import urllib.parse
import json
import os
import time
import re



## 테스트 시나리오
"""의약품 검색 > 장바구니 추가 > 주문창에서 좌측 판매금액 + 금융할인 + 주문금액 각각 더한 후 우측 결제정보에서 금액 체크
시간 남으면 앱에서 order쏴서 받는 금액들 세팅값과 2차 검증 진행"""

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
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "오늘 하루 그만보기")]'))
        )
        close_today_btn.click()
        time.sleep(3)

        click_order_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "baropharmOrder"))
        )
        click_order_btn.click()
        print("\n함께배송 오늘하루 보지않기 방어")
        time.sleep(3)

    except Exception as e:
        print("함께배송 오늘하루 보지않기 팝업 미노출")

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
    print(f"결제 혜택 변경 성공 {value_benefit}")
    print("=== PATCH 요청 정보 ===")
    print("URL:", url)
    print("Payload:", payload)
    print("Headers:", headers)
    print("Status Code:", response.status_code)
    print("Response Text:", response.text)

    if response.status_code == 204:
        return True
    return response.json()




"""
테스트 시나리오
1. 상품 검색 (의약품, 외품, 제품)
    - 검색된 상품 장바구니에서 최종으로 확인
    assert 확인 제목이나 상품 id 값으로
2. 장바구니 추가

"""


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


def test_login(driver):

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



def test_add_products_cartitems(driver):

    click_order_tab = WebDriverWait(driver, 10).until(
        EC. element_to_be_clickable((By.XPATH, '//img[@alt="주문하기"]/parent::a'))
    )
    click_order_tab.click()
    time.sleep(3)
    assert "/order" in driver.current_url, "주문하기 진입 실패"
    print("\n주문하기 진입 성고")

    search_directly_by_url(driver, "쿠퍼")
    time.sleep(3)


    click_product_by_name(driver, "쿠퍼 QUASIDRUG")
    time.sleep(3)

    input_inventory_unit(driver, "4129283", 10)
    print("의약외품 장바구니 추가")
    time.sleep(3)

    confirm_already_cartitem_btn(driver)
    time.sleep(3)

    click_product_by_name(driver, "쿠퍼 ETC")
    print("제품도매 일반의약품 장바구니 추가")
    time.sleep(3)

    input_inventory_unit(driver, "4129487", 10)
    time.sleep(3)

    confirm_already_cartitem_btn(driver)
    time.sleep(3)

    click_product_by_name(driver, "쿠퍼_리뷰가 많은 상품")
    print("제품상품 장바구니 추가")
    time.sleep(3)

    input_inventory_unit(driver, "4129492", 10)
    time.sleep(3)

    confirm_already_cartitem_btn(driver)
    time.sleep(3)

    click_product_by_name(driver, "쿠퍼_로수반정(병) 10mg 28T_520원")
    print("의약품도매 상품 장바구니 추가")
    time.sleep(3)

    input_inventory_unit(driver, "4129447", 10)
    time.sleep(3)

    confirm_already_cartitem_btn(driver)
    time.sleep(3)

def test_wait_for_payment_popup(driver):
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
    print(f"확인할 문자열 : {check_order_popup.text}")


def test_pt01_deposit_pay(driver):

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
            '(//li[.//p[contains(text(),"카드 결제금액")]]//strong | //li[.//p[contains(text(),"카드 결제금액")]]//span)[last()]'
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
    assert total_order_sum == right_total_sale_amount, "좌측 도매금액과 우측 결제금액 총합 불일치"
    print(f"\n도매영역 판매금액 : {total_order_sum}, 결제영역 판매금액 : {right_total_sale_amount}\n도매영역 할인금액 : {total_fin_disscout_sum}, 결제 영역 할인 금액 : {right_discount_total}")
    print(f"\n카드 결제 금액 : {total_amount_elem}, 포인트 결제 금액 : {points}, 예치금 결제 금액 : {deposit}")
    time.sleep(5)


def test_deposit_payment(driver):

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
    print("예치금 결제 성공")
    time.sleep(3)

    home_btn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "svg.main-logo"))
    )
    home_btn.click()
    time.sleep(1)

@pytest.mark.testcode
def test_charge_deposit(driver):

    token = cms_token_get()
    charge = charge_deposit(token)
    assert charge is not None
    time.sleep(3)






#카드결제 확인용

def test_switch_payment_benefit(driver):

    token = cms_token_get()
    switch = payment_benefits_switch_mode(token, True)

    print("결제혜택 ON, 국민카드")
    assert switch is True
    time.sleep(3)

def test_add_products_cartitems(driver):

    click_order_tab = WebDriverWait(driver, 10).until(
        EC. element_to_be_clickable((By.XPATH, '//img[@alt="주문하기"]/parent::a'))
    )
    click_order_tab.click()
    time.sleep(3)
    assert "/order" in driver.current_url, "주문하기 진입 실패"
    print("\n주문하기 진입 성공")

    search_directly_by_url(driver, "쿠퍼")
    time.sleep(3)


    click_product_by_name(driver, "쿠퍼 QUASIDRUG")
    time.sleep(3)

    input_inventory_unit(driver, "4129283", 10)
    print("의약외품 장바구니 추가")
    time.sleep(3)

    confirm_already_cartitem_btn(driver)
    time.sleep(3)

    click_product_by_name(driver, "쿠퍼 ETC")
    print("제품도매 일반의약품 장바구니 추가")
    time.sleep(3)

    input_inventory_unit(driver, "4129487", 10)
    time.sleep(3)

    confirm_already_cartitem_btn(driver)
    time.sleep(3)

    click_product_by_name(driver, "쿠퍼_리뷰가 많은 상품")
    print("제품상품 장바구니 추가")
    time.sleep(3)

    input_inventory_unit(driver, "4129492", 10)
    time.sleep(3)

    confirm_already_cartitem_btn(driver)
    time.sleep(3)

    click_product_by_name(driver, "쿠퍼_로수반정(병) 10mg 28T_520원")
    print("의약품도매 상품 장바구니 추가")
    time.sleep(3)

    input_inventory_unit(driver, "4129447", 10)
    time.sleep(3)

    confirm_already_cartitem_btn(driver)
    time.sleep(3)

def test_wait_for_payment_popup(driver):
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
    print(f"확인할 문자열 : {check_order_popup.text}")


def test_pt01_deposit_pay(driver):

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
            '(//li[.//p[contains(text(),"카드 결제금액")]]//strong | //li[.//p[contains(text(),"카드 결제금액")]]//span)[last()]'
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
    #assert total_order_sum == right_total_sale_amount, "좌측 도매금액과 우측 결제금액 총합 불일치"
    print(f"\n도매영역 판매금액 : {total_order_sum}, 결제영역 판매금액 : {right_total_sale_amount}\n도매영역 할인금액 : {total_fin_disscout_sum}, 결제 영역 할인 금액 : {right_discount_total}")
    print(f"\n카드 결제 금액 : {total_amount_elem}, 포인트 결제 금액 : {points}, 예치금 결제 금액 : {deposit}")
    time.sleep(5)


def test_deposit_payment(driver):

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

def test_switch_payment_benefit_off(driver):

    token = cms_token_get()
    switch = payment_benefits_switch_mode(token, False)

    print("결제혜택 off, 국민카드")
    assert switch is True
    time.sleep(3)






















"""
#예치금 초기화때 사용
def test_deposit_to_zero(driver):
    input_box = driver.find_elements(By.CSS_SELECTOR, "input.input-box.small[type='search']")
    input_box[1].clear()
    assert input_box[1].text == "", "예치금 초기화 실패"
    print("예치금 초기화 성공")
    time.sleep(3)
"""











