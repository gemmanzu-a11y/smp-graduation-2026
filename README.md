# SMP 졸업작품 공동 작업

육지 시간별 SMP의 D+1·D+2·D+3, 총 72시간 예측 연구입니다.

- `1120gradpj/`: 데이터 수집 코드, 모델 구현, 검증 코드와 보고서
- `presentation/`: 발표자료
- `v20/`: 기존 팀 프로젝트 저장소 참조(submodule)
- `GITHUB_SHARING.md`: 자동 공유 범위·중지·재시작 방법

```bash
git clone --recurse-submodules https://github.com/gemmanzu-a11y/smp-graduation-2026.git
```

API 키·가상환경·원자료·학습 모델 바이너리는 저장소에 포함하지 않습니다. 모델 실행에 필요한 자료는 별도로 준비해야 합니다. 실행 방법과 과거 실험의 한계는 `1120gradpj/README.md` 및 각 모델 설명서를 확인하세요.

관리자 Mac에서는 저장된 변경사항을 5분마다 자동 커밋·업로드합니다. 팀원 변경은 별도 브랜치와 PR로 공유하세요. 자동 동기화는 원격 변경을 강제로 덮어쓰지 않습니다.
