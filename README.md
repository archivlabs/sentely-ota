# sentely-ota

Sentely 앱의 **문장 세트 받기**(설정 → 데이터 관리 → 문장 세트 받기)에 나오는 문장 세트입니다.
앱은 `https://sentely.archivseoul.com/ota/...`를 요청하고, 서버가 이 저장소의 GitHub Pages로
넘겨 줍니다. 이 저장소에 push하면 앱을 다시 내지 않아도 새 세트가 보입니다.

## 구성

| 경로 | 내용 |
|---|---|
| `sources/sets.json` | 세트 목록. 적힌 순서대로 앱에 보입니다. |
| `sources/<id>.txt` | 세트의 문장 |
| `sources/<id>/01.mp3` … | 문장 순서대로의 녹음 (선택) |
| `scripts/build.py` | `sources/`에서 `ota/`를 만듭니다. |
| `ota/` | 앱이 받는 파일 (`sets.json`, `<id>.sentely`). 직접 고치지 않습니다. |

## 세트 추가

1. `sources/<id>.txt`에 한 줄에 한 문장씩 씁니다. 문장 바로 아래 줄에 `(번역)`, `- 출처`, `* 메모`를
   붙일 수 있고, 빈 줄과 `#`으로 시작하는 줄은 무시됩니다.
2. 녹음이 있으면 `sources/<id>/01.mp3`처럼 문장 번호로 넣습니다(`.m4a`도 됩니다).
   합성 음성이면 세트 설명에 그렇다고 적습니다.
3. `sources/sets.json`에 항목을 넣습니다.

   ```json
   {
     "id": "everyday-1",
     "name": {"en": "Everyday 1", "ko": "일상 1"},
     "summary": {"en": "Short sentences for every day", "ko": "매일 쓰는 짧은 문장"},
     "audience": "adult",
     "source": "everyday-1.txt"
   }
   ```

   - `id`는 파일 이름이 되고, 앱이 "추가됨"을 기억하는 값입니다. 다른 세트에 다시 쓰지 않습니다.
   - `audience`: `adult`(성인 모드), `child`(아동 모드), `all`(둘 다)
   - 이름과 설명은 `en`, `ko`, `ja`, `zh-Hans`, `zh-Hant`. 없는 언어는 영어로 보입니다.
   - 앱에서 녹음까지 담아 공유한 `.sentely` 파일을 `source`로 써도 됩니다.
4. `python3 scripts/build.py`를 돌리고, `sources/`와 `ota/`를 함께 커밋해 push합니다.
   GitHub Pages 캐시 때문에 앱에 보이기까지 몇 분 걸릴 수 있습니다.

같은 입력이면 `build.py`는 같은 파일을 만들기 때문에, 바뀐 세트만 `sha256`이 바뀝니다.
앱은 받은 파일이 목록의 `sha256`과 맞을 때만 가져옵니다.

## 저작권

문장은 모두 새로 쓴 것이고, 녹음은 AI 음성으로 만든 것입니다. 라이선스를 붙이지 않았습니다
(All rights reserved).
