import requests
import csv
import json

# 🔑 제공해주신 키를 여기에 정확히 반영합니다.
DATA_SERVICE_KEY = 'RTvJj35/XhTdV0L7mYhP21h3Ei/NBkyBcTZQ2SyJSIl+e6K2qVvO2Eqvfe55wU/3y3z9WofPq52uuZUkP27jjA=='

# 새로운 API 엔드포인트를 사용합니다.
base_url = "https://apis.data.go.kr/1543061/animalShelterSrvc_v2"

params = {
    'serviceKey': DATA_SERVICE_KEY,
    'pageNo': '1',
    'numOfRows': '100',
    '_type': 'json'
}

def fetch_and_save_data():
    try:
        print("API 호출을 시도합니다...")
        response = requests.get(base_url, params=params)
        response.raise_for_status()

        data = response.json()
        items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])

        if not items:
            print("❌ API 호출은 성공했으나, 데이터가 없습니다.")
            return

        with open('animal_data_new.csv', 'w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            headers = items[0].keys()
            writer.writerow(headers)
            for item in items:
                row = [item.get(key, '') for key in headers]
                writer.writerow(row)

        print(f"🎉 성공! {len(items)}개의 데이터를 'animal_data_new.csv' 파일에 저장했습니다.")

    except requests.exceptions.RequestException as e:
        print(f"❌ API 호출 실패: {e}")
        print("키가 유효하지 않거나, 네트워크에 문제가 있을 수 있습니다.")
    except Exception as e:
        print(f"❌ 데이터 처리 중 오류 발생: {e}")

if __name__ == "__main__":
    fetch_and_save_data()