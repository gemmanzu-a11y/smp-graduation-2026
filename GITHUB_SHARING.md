# GitHub 자동 공유

이 Mac에 로그인한 동안 5분마다 이 폴더의 변경사항을 자동 커밋하고 origin으로 push합니다. 저장되지 않은 편집 내용은 포함되지 않습니다. 잠자기·오프라인 동안에는 즉시 반영되지 않으며 다음 실행에서 재시도합니다.

자동 업로드는 `scripts/github_sync.py`가 담당합니다. API 키, 가상환경, 원자료와 학습 모델 파일은 제외합니다. 소스코드, 설정 예제, 설명서, tests 및 제외 대상이 아닌 보고서를 공유합니다. 데이터·학습 바이너리는 별도 공유가 필요합니다. 팀원은 requirements로 환경을 만들고 자신의 .env를 설정합니다.

수동 동기화: `python3 scripts/github_sync.py`
상태: `launchctl print gui/$(id -u)/com.mj.smp-graduation-2026.sync`
로그: `.git-sync/launchd.log`, `.git-sync/launchd-error.log`
일시 중지: `launchctl bootout gui/$(id -u)/com.mj.smp-graduation-2026.sync`
재시작: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mj.smp-graduation-2026.sync.plist`

원격에 다른 사람이 올린 변경이 있으면 push가 거절될 수 있습니다. 자동으로 pull·merge·force-push하지 않고 중단합니다. Git 상태를 확인해 수동 통합한 뒤 동기화를 다시 실행하세요. 로컬 변경·삭제도 커밋됩니다. 팀원은 별도 브랜치에서 작업하고 PR로 합치는 편이 좋습니다.

업로드 전 검사에서 인증키 형태가 발견되거나 파일이 5 MiB를 넘으면 중단합니다. 패턴 검사는 모든 비밀정보를 탐지하지 못하므로 인증키는 .env에만 보관하세요. GitHub 저장소는 공개입니다.

기존 `v20`은 팀원의 별도 저장소를 참조하는 submodule로 보존합니다. 이 자동 업로드는 v20 내부 수정의 커밋·푸시를 수행하지 않습니다. 전체 받기: `git clone --recurse-submodules https://github.com/gemmanzu-a11y/smp-graduation-2026.git`
