# Commurank Analytics

커뮤랭크는 Google Analytics 4를 사용한다.

- Measurement ID: `G-46ZQT4LDSD`
- 설정 파일: `analytics-config.json`
- 공통 로더: `analytics.js`
- 검색어 원문이나 원문 게시글 URL 전체를 GA4 커스텀 이벤트에 보내지 않는다.

## 기본 측정

- `page_view`: GA4 기본 페이지 조회
- `content_group`: Home, Daily Briefing, Weekly Reports, Monthly Reports, Ranking Archive, Community Ranking, Issues, Search, My Feed, Post Analysis, Info 단위로 콘텐츠 묶음

## 커뮤랭크 커스텀 이벤트

- `original_outbound_click`: 각 커뮤니티 원문으로 직접 이동
  - 전체 URL 대신 목적지 도메인, 출처, 커뮤랭크 내 출발 페이지를 기록
- `search_submit`: 통합 검색 실행
  - 검색어 자체가 아니라 글자 수만 기록
- `ranking_period_change`: 실시간·급상승·일간·주간·월간 전환
- `category_filter`: 카테고리 필터 사용
- `keyword_filter`: 인기 키워드 필터 사용
- `source_filter_change`: 커뮤니티 필터 변경
- `search_sort_change`: 검색 결과 정렬 변경
- `ranking_archive_select`: 과거 게시글 랭킹 선택
- `issue_archive_select`: 과거 이슈 랭킹 선택
- `briefing_archive_select`: 과거 브리핑 선택
- `post_analysis_open`: 게시글 분석 화면 진입
- `issue_open`: 개별 이슈 분석 진입
- `issue_ranking_open`: 이슈 TOP20 진입
- `briefing_open`: 일간 브리핑 이동
- `weekly_report_open`: 주간 트렌드 리포트 이동
- `monthly_report_open`: 월간 트렌드 리포트 이동
- `ranking_archive_open`: 랭킹 아카이브 이동
- `community_open`: 커뮤니티 전용 랭킹 이동

## 운영 시 먼저 볼 지표

1. 사용자 및 조회수
2. 신규 사용자와 재방문 흐름
3. Organic Search 유입
4. 콘텐츠 그룹별 조회수와 참여
5. `original_outbound_click` 수
6. `search_submit` 수
7. 일간·주간·월간 리포트 페이지 성과

애드센스 승인 여부는 특정 방문자 수 하나로 판단하지 않는다. 자체 콘텐츠 축적, 검색 색인 상태, 정책 페이지, 사이트 이용성 등을 함께 유지한 뒤 신청한다.
