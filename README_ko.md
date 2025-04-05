<p align="center">
  <img src="assets/logo.jpg" width="200"/>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README_zh.md">中文</a> | 한국어 | <a href="README_ja.md">日本語</a>
</p>

<p align="center">
  <a href="https://github.com/mannaandpoem/OpenManus/stargazers"><img src="https://img.shields.io/github/stars/mannaandpoem/OpenManus?style=social" alt="GitHub stars"></a>
  &ensp;
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  &ensp;
  <a href="https://discord.gg/DYn29wFk9z"><img src="https://dcbadge.vercel.app/api/server/DYn29wFk9z?style=flat" alt="Discord Follow"></a>
  &ensp;
  <a href="https://huggingface.co/spaces/lyh-917/OpenManusDemo"><img src="https://img.shields.io/badge/Demo-Hugging%20Face-yellow" alt="Demo"></a>
</p>

# 👋 OpenManus

Manus는 놀라운 도구지만, OpenManus는 *초대 코드* 없이도 모든 아이디어를 실현할 수 있습니다! 🛫

우리 팀의 멤버인 [@Xinbin Liang](https://github.com/mannaandpoem)와 [@Jinyu Xiang](https://github.com/XiangJinyu) (핵심 작성자), 그리고 [@Zhaoyang Yu](https://github.com/MoshiQAQ), [@Jiayi Zhang](https://github.com/didiforgithub), [@Sirui Hong](https://github.com/stellaHSR)이 함께 했습니다. 우리는 [@MetaGPT](https://github.com/geekan/MetaGPT)로부터 왔습니다. 프로토타입은 단 3시간 만에 출시되었으며, 계속해서 발전하고 있습니다!

이 프로젝트는 간단한 구현에서 시작되었으며, 여러분의 제안, 기여 및 피드백을 환영합니다!

OpenManus를 통해 여러분만의 에이전트를 즐겨보세요!

또한 [OpenManus-RL](https://github.com/OpenManus/OpenManus-RL)을 소개하게 되어 기쁩니다. OpenManus와 UIUC 연구자들이 공동 개발한 이 오픈소스 프로젝트는 LLM 에이전트에 대해 강화 학습(RL) 기반 (예: GRPO) 튜닝 방법을 제공합니다.

## 프로젝트 데모

<video src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" data-canonical-src="https://private-user-images.githubusercontent.com/61239030/420168772-6dcfd0d2-9142-45d9-b74e-d10aa75073c6.mp4?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NDEzMTgwNTksIm5iZiI6MTc0MTMxNzc1OSwicGF0aCI6Ii82MTIzOTAzMC80MjAxNjg3NzItNmRjZmQwZDItOTE0Mi00NWQ5LWI3NGUtZDEwYWE3NTA3M2M2Lm1wND9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNTAzMDclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjUwMzA3VDAzMjIzOVomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTdiZjFkNjlmYWNjMmEzOTliM2Y3M2VlYjgyNDRlZDJmOWE3NWZhZjE1MzhiZWY4YmQ3NjdkNTYwYTU5ZDA2MzYmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0In0.UuHQCgWYkh0OQq9qsUWqGsUbhG3i9jcZDAMeHjLt5T4" controls="controls" muted="muted" class="d-block rounded-bottom-2 border-top width-fit" style="max-height:640px; min-height: 200px"></video>

## ✨ 특징 (추가됨)

*   **멀티턴 대화**: 컨텍스트를 유지하며 확장된 대화를 진행할 수 있습니다.
*   **웹 UI (Gradio)**: 직관적인 웹 인터페이스를 통해 에이전트와 상호 작용합니다. 다음 기능이 포함됩니다:
    *   실시간 업데이트를 위한 스트리밍 응답.
    *   세션 관리 (대화 생성, 이름 변경, 삭제, 전환).
    *   로컬 `chatsHistory/` 디렉토리에 자동으로 저장되는 영구적인 채팅 기록.
*   **OpenAI 호환 API (FastAPI)**: 익숙한 OpenAI SDK 형식(`/v1/chat/completions` 엔드포인트)을 사용하여 OpenManus를 애플리케이션에 통합합니다. 스트리밍 및 비스트리밍 모드를 모두 지원합니다.
*   **명령줄 인터페이스 (CLI)**: 순수한 터미널 상호 작용 방식을 제공합니다.
*   **다양한 도구**: 다음 작업을 위한 도구를 갖추고 있습니다:
    *   웹 브라우징 (`BrowserUseTool`)
    *   코드 실행 (샌드박스 환경의 Python)
    *   파일 작업 (문자열 교체 편집기)
    *   웹 검색 (Google, Bing, DuckDuckGo, Baidu)
    *   Bash 명령어 실행 (샌드박스 터미널 경유)
*   **확장 가능한 프레임워크**: 명확한 객체 지향 구조로 구축되었습니다 (`BaseAgent` -> `ReActAgent` -> `ToolCallAgent` -> `BrowserAgent` -> `Manus`).

## 📸 스크린샷 (추가됨)

**웹 UI:**
![OpenManus 웹 UI 스크린샷 1](https://github.com/Hank-Chromela/Hank-Chroela-images/blob/main/1743753144854.png?raw=true)

**세션 관리:**
![OpenManus 웹 UI 스크린샷 2](https://github.com/Hank-Chromela/Hank-Chroela-images/blob/main/1743753160804.png?raw=true)

## 🚀 설치 방법

두 가지 설치 방법을 제공합니다. **방법 2 (uv 사용)** 이 더 빠른 설치와 효율적인 종속성 관리를 위해 권장됩니다.

### 방법 1: conda 사용

1.  새로운 conda 환경을 생성합니다:
    ```bash
    conda create -n open_manus python=3.12 -y
    conda activate open_manus
    ```
2.  저장소를 클론합니다:
    ```bash
    git clone https://github.com/Hank-Chromela/OpenManus-GUI.git # 당신의 Fork를 클론하세요
    cd OpenManus-GUI
    ```
3.  종속성을 설치합니다:
    ```bash
    pip install -r requirements.txt
    ```

### 방법 2: uv 사용 (권장)

1.  uv를 설치합니다. (빠른 Python 패키지 설치 및 종속성 관리 도구):
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
2.  저장소를 클론합니다:
    ```bash
    git clone https://github.com/Hank-Chromela/OpenManus-GUI.git # 당신의 Fork를 클론하세요
    cd OpenManus-GUI
    ```
3.  새로운 가상 환경을 생성하고 활성화합니다:
    ```bash
    uv venv --python 3.12
    source .venv/bin/activate  # Unix/macOS의 경우
    # .venv\Scripts\activate    # Windows의 경우
    ```
4.  종속성을 설치합니다:
    ```bash
    uv pip install -r requirements.txt
    ```

### 브라우저 자동화 도구 (필수)

```bash
playwright install --with-deps
⚙️ 설정 방법
OpenManus를 사용하려면 사용하는 LLM API에 대한 설정이 필요합니다. 아래 단계를 따라 설정을 완료하세요:

config/config.example.toml 파일 확인: 이 파일은 설정 템플릿입니다.
config/config.toml 파일 생성:
cp config/config.example.toml config/config.toml
config/config.toml 편집: API 키를 추가하고 설정을 커스터마이징하세요:
# 전역 LLM 설정 (주로 default 사용)
[llm.default]
model = "gpt-4o" # 예: gpt-4o, gpt-3.5-turbo, claude-3-opus-20240229 등
api_type = "openai" # "openai", "azure", "aws" (Bedrock) 등 지원, LLM 설정에 따라 다름
base_url = "https://api.openai.com/v1" # API 주소로 교체
api_key = "sk-..."  # 중요: 실제 API 키로 교체하세요!
max_tokens = 4096
temperature = 0.0
# api_version = "..." # Azure OpenAI 사용 시 필요

# 특정 LLM 모델에 대한 선택적 설정 (예: 비전 작업용)
# [llm.vision]
# model = "gpt-4o"
# base_url = "https://api.openai.com/v1"
# api_key = "sk-..."
참고: config/config.toml 파일은 민감한 정보를 포함하므로 .gitignore에 추가되어 버전 관리에서 제외됩니다.
▶️ 애플리케이션 실행 (업데이트됨)
이제 다른 시작 파일을 통해 다른 모드를 시작할 수 있습니다:

1. 웹 UI 및 API 서버 시작 (권장)

main.py 스크립트를 실행합니다:

python main.py
# 또는 명시적으로 all 지정 (기본 동작)
# python main.py --service all
이 명령은 다음을 수행합니다:

Gradio 웹 UI 서버 시작 (기본 리슨 주소 http://127.0.0.1:7860).
FastAPI API 서버 시작 (기본 리슨 주소 http://0.0.0.0:8000).
브라우저에서 웹 UI 자동 열기 시도.
2. 웹 UI만 시작

python main.py --service ui
Gradio 웹 UI 서버만 시작 (기본 http://127.0.0.1:7860).
브라우저 자동 열기 시도.
3. API 서버만 시작

python main.py --service api
FastAPI API 서버만 시작 (기본 http://0.0.0.0:8000).
4. 명령줄 인터페이스 (CLI) 실행

python cli_main.py
순수 명령줄 인터페이스 시작.
💻 웹 UI 사용법 (추가됨)
브라우저가 자동으로 열리지 않으면 수동으로 http://127.0.0.1:7860으로 이동하십시오.
채팅: 하단의 메시지 상자에 요청을 입력하고 Enter 키를 누르거나 "보내기"를 클릭합니다. 에이전트의 생각 과정, 도구 사용 및 최종 응답이 채팅 창으로 스트리밍됩니다.
세션 관리:
왼쪽 사이드바를 사용하여 대화를 관리합니다.
"➕ 새 채팅"을 클릭하여 새 대화를 시작합니다.
목록에서 세션을 선택하여 해당 기록을 로드합니다.
목록 아래의 "선택한 세션 관리" 섹션을 사용하여 현재 선택된 채팅의 이름을 변경하거나 삭제합니다 (마지막 남은 채팅은 삭제할 수 없습니다).
영구성: 채팅 기록 및 세션 이름은 JSON 파일로 chatsHistory/ 디렉토리에 자동으로 저장되며 애플리케이션을 다시 시작할 때 다시 로드됩니다.
🔌 API 사용법 (추가됨)
서버는 /v1/chat/completions에서 OpenAI 호환 API 엔드포인트를 노출합니다 (기본 실행 주소 http://0.0.0.0:8000). 표준 OpenAI 클라이언트 라이브러리(예: 공식 Python openai 라이브러리)를 사용하여 상호 작용할 수 있습니다.

클라이언트 설정:

Base URL: http://<서버 IP 또는 localhost>:8000/v1 (예: http://127.0.0.1:8000/v1)
API Key: 비어 있지 않은 모든 문자열 (예: "not-needed"). 서버는 이 키를 검증하지 않습니다.
Model: 비어 있지 않은 모든 문자열 (예: "openmanus"). 서버는 이 모델 이름을 무시하고 설정된 Manus 에이전트를 사용합니다.
openai Python 라이브러리 사용 예제:

# test_api.py
import openai

# 클라이언트 설정 (API 서버가 로컬 8000 포트에서 실행 중이라고 가정)
client = openai.OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="not-needed", # 더미 키 제공
)

# 비스트리밍 요청
try:
    completion = client.chat.completions.create(
        model="openmanus-local", # 모델 이름은 필수지만 서버에서 무시됨
        messages=[
            {"role": "user", "content": "프랑스의 수도는 어디인가요?"}
        ]
    )
    print("비스트리밍 응답:")
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"API 오류: {e}")

# 스트리밍 요청
try:
    stream = client.chat.completions.create(
        model="openmanus-local",
        messages=[
            {"role": "user", "content": "양자 얽힘에 대해 간략하게 설명해주세요."}
        ],
        stream=True
    )
    print("\n스트리밍 응답:")
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end="")
    print()
except Exception as e:
    print(f"API 스트리밍 오류: {e}")
🙌 기여 방법
모든 친절한 제안과 유용한 기여를 환영합니다! 이슈를 생성하거나 풀 리퀘스트를 제출해 주세요.

또는 📧 메일로 연락주세요. @mannaandpoem : mannaandpoem@gmail.com

참고: pull request를 제출하기 전에 pre-commit 도구를 사용하여 변경 사항을 확인하십시오. pre-commit run --all-files를 실행하여 검사를 실행합니다.

💬 커뮤니티 그룹
Feishu 네트워킹 그룹에 참여하여 다른 개발자들과 경험을 공유하세요!

⭐ Star History
Star History Chart

🙏 감사의 글
이 프로젝트에 기본적인 지원을 제공해 주신 anthropic-computer-use와 browser-use에게 감사드립니다!

또한, AAAJ, MetaGPT, OpenHands, SWE-agent에 깊은 감사를 드립니다.

또한 Hugging Face 데모 공간을 지원해 주신 阶跃星辰 (stepfun)에게 감사드립니다.

OpenManus는 MetaGPT 기여자들에 의해 개발되었습니다. 이 에이전트 커뮤니티에 깊은 감사를 전합니다!

📜 인용
연구나 작업에 OpenManus를 사용하는 경우 다음과 같이 인용하십시오:

@misc{openmanus2025,
  author = {Xinbin Liang and Jinyu Xiang and Zhaoyang Yu and Jiayi Zhang and Sirui Hong and Hank-Chromela (UI/API Integration)},
  title = {OpenManus: UI 및 API를 갖춘 다재다능한 AI 에이전트를 위한 오픈 소스 프레임워크},
  year = {2025},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/mannaandpoem/OpenManus}},
}
