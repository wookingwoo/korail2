import os
import random
import requests
from time import sleep
from korail2 import Korail, NoResultsError, SoldOutError
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수에서 값 가져오기
KORAIL_PHONE = os.getenv("KORAIL_PHONE")
KORAIL_PASSWORD = os.getenv("KORAIL_PASSWORD")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# 노선 정보 목록
routes = [
    {
        "DEP_STATION": "전주",
        "ARR_STATION": "서울",
        "TRAVEL_DATE": "20240917",
        "TRAVEL_TIME": "193000",
    },
    {
        "DEP_STATION": "광주송정",
        "ARR_STATION": "서울",
        "TRAVEL_DATE": "20240918",
        "TRAVEL_TIME": "090000",
    },
    # 필요한 만큼 노선 추가 가능
]

MAX_RETRIES = 3  # 최대 재시도 횟수
SLEEP_MIN = 5  # 대기 시간 최소값 (초)
SLEEP_MAX = 10  # 대기 시간 최대값 (초)

korail = Korail(KORAIL_PHONE, KORAIL_PASSWORD)
korail.login()


def send_slack_message(message):
    """슬랙 메시지를 웹훅을 통해 전송하는 함수"""
    payload = {"text": message}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"슬랙 메시지 전송 중 에러 발생: {e}")


def attempt_reservation(route):
    """좌석 예약 시도 및 성공 시 슬랙 메시지 전송"""
    DEP_STATION = route["DEP_STATION"]
    ARR_STATION = route["ARR_STATION"]
    TRAVEL_DATE = route["TRAVEL_DATE"]
    TRAVEL_TIME = route["TRAVEL_TIME"]

    try:
        trains = korail.search_train(
            DEP_STATION,
            ARR_STATION,
            TRAVEL_DATE,
            TRAVEL_TIME,
            include_no_seats=False,
        )
        seat = korail.reserve(trains[0])
        print(
            f"\n기차 좌석 예약 성공! {DEP_STATION} -> {ARR_STATION}, 날짜: {TRAVEL_DATE}, 시간: {TRAVEL_TIME}\n좌석: {seat}"
        )
        send_slack_message(
            f":tada: 기차 좌석 예약 성공! {DEP_STATION} -> {ARR_STATION}, 날짜: {TRAVEL_DATE}, 시간: {TRAVEL_TIME}\n좌석: {seat}"
        )
        return True

    except NoResultsError:
        # 잔여 좌석이 없을 때의 에러 처리
        print(f"잔여 좌석이 없습니다.", end=" ")

    except SoldOutError:
        # 매진 에러 처리
        print(f"매진되었습니다.", end=" ")

    except Exception as e:
        send_slack_message(f"기타 에러 발생: {e}")
        return False

    return False


if __name__ == "__main__":
    current_retry = 0

    while current_retry < MAX_RETRIES:
        # 노선 선택: 현재 시도하는 횟수에 따라 순차적으로 노선 선택
        route = routes[current_retry % len(routes)]

        print(
            f"\n[{current_retry + 1}/{MAX_RETRIES}] {route['DEP_STATION']} -> {route['ARR_STATION']}, 날짜: {route['TRAVEL_DATE']}, 시간: {route['TRAVEL_TIME']}"
        )

        success = attempt_reservation(route)
        if success:
            print("예약 성공! 예약 프로세스를 중단합니다.")
            break

        # 시도 횟수 증가
        current_retry += 1

        # 랜덤한 대기 시간 설정
        wait_time = random.uniform(SLEEP_MIN, SLEEP_MAX)
        print(f"{wait_time:.2f}초 후에 다시 시도합니다..")
        sleep(wait_time)

    if current_retry == MAX_RETRIES:
        print(
            f"\n최대 {MAX_RETRIES}번 시도했으나 모든 노선에서 좌석 예약에 실패했습니다."
        )
        send_slack_message(
            f":man-gesturing-no: 최대 {MAX_RETRIES}번 시도했으나 모든 노선에서 좌석 예약에 실패했습니다."
        )
