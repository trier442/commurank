# Commurank AdSense

커뮤랭크의 Google AdSense 연결은 현재 승인 전 상태이므로 비활성화되어 있다.

## 현재 상태

- 설정 파일: `ads-config.json`
- 공통 로더: `ads.js`
- `enabled: false`
- 게시자 ID는 아직 등록하지 않음
- 광고 스크립트는 현재 방문자 브라우저에서 로드되지 않음

## 승인 후 적용 순서

1. Google AdSense에서 사이트 `commurank.kr` 승인을 확인한다.
2. 게시자 ID `ca-pub-...`를 확인한다.
3. `ads-config.json`의 `client_id`에 게시자 ID를 넣고 `enabled`를 `true`로 바꾼다.
4. AdSense가 제공하는 ads.txt 항목을 루트 `/ads.txt`에 추가한다.
5. 배포 후 `https://commurank.kr/ads.txt`가 정상 노출되는지 확인한다.
6. Google AdSense에서 사이트 상태와 광고 게재 상태를 확인한다.

현재는 Auto Ads 방식에 맞춰 공통 AdSense 스크립트만 준비해 두었으며, 승인 전에는 빈 광고 자리나 광고 스크립트를 표시하지 않는다.
