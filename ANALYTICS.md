# Commurank Analytics

커뮤랭크의 방문자 분석은 기본값에서 비활성화되어 있다.

## 연결

1. Google Analytics 4에서 웹 데이터 스트림을 만든다.
2. Measurement ID를 확인한다. 형식은 `G-XXXXXXXXXX`이다.
3. GitHub Actions에서 **Configure Commurank Analytics**를 실행한다.
4. `ga4_id`에 Measurement ID를 입력한다.
5. 빈 값으로 실행하면 분석 기능이 다시 비활성화된다.

## 기록 이벤트

- `page_view`: GA4 기본 페이지 조회
- `post_analysis_open`: 게시글 상세 분석 진입
- `issue_open`: 개별 이슈 분석 진입
- `issue_ranking_open`: 이슈 TOP20 진입
- `briefing_open`: 오늘의 브리핑 진입
- `community_open`: 커뮤니티 전용 랭킹 이동
- `original_outbound_click`: 원문 사이트로 이동
- `search_submit`: 통합 검색 실행
- `keyword_filter`: 인기 키워드 필터 사용
- `ranking_archive_select`: 과거 게시글 랭킹 선택
- `issue_archive_select`: 과거 이슈 랭킹 선택
- `briefing_archive_select`: 과거 브리핑 선택
- `source_filter_change`: 커뮤니티 필터 변경
- `search_sort_change`: 검색 결과 정렬 변경

## 개인정보 최소화

검색어 원문은 GA4 이벤트로 보내지 않는다. 검색 실행 시 검색어 길이만 기록한다.
원문 링크 클릭 시 전체 URL이 아니라 목적지 도메인만 커스텀 이벤트 매개변수로 기록한다.
