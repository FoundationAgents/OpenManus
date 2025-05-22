# 차트 시각화 도구

차트 시각화 도구는 Python을 통해 데이터 처리 코드를 생성하고, 최종적으로 [@visactor/vmind](https://github.com/VisActor/VMind)를 호출하여 차트 사양을 얻습니다. 차트 렌더링은 [@visactor/vchart](https://github.com/VisActor/VChart)를 사용하여 구현됩니다.

## 설치 (Mac / Linux)

1. Node.js 18 이상 설치

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# nvm 활성화, 예를 들어 Bash
source ~/.bashrc
# 그런 다음 최신 안정 버전의 Node 설치
nvm install node
# 사용 활성화, 예를 들어 최신 안정 버전이 22인 경우 use 22
nvm use 22
```

2. 의존성 설치

```bash
# 현재 저장소에서 해당 위치로 이동
cd app/tool/chart_visualization
npm install
```

## 설치 (Windows)
1. nvm-windows 설치

    [공식 GitHub 페이지](https://github.com/coreybutler/nvm-windows?tab=readme-ov-file#readme)에서 최신 버전의 `nvm-setup.exe`를 다운로드하고 설치합니다.

2. nvm을 사용하여 Node.js 설치

```powershell
# 그런 다음 최신 안정 버전의 Node 설치
nvm install node
# 사용 활성화, 예를 들어 최신 안정 버전이 22인 경우 use 22
nvm use 22
```

3. 의존성 설치

```bash
# 현재 저장소에서 해당 위치로 이동
cd app/tool/chart_visualization
npm install
```

## 도구
### python_execute

Python 코드를 사용하여 데이터 분석의 필요한 부분(데이터 시각화 제외)을 실행합니다. 여기에는 데이터 처리, 데이터 요약, 보고서 생성 및 일부 일반적인 Python 스크립트 코드가 포함됩니다.

#### 입력
```typescript
{
  // 코드 유형: 데이터 처리/데이터 보고서/기타 일반 작업
  code_type: "process" | "report" | "others"
  // 최종 실행 코드
  code: string;
}
```

#### 출력
Python 실행 결과, 중간 파일 저장 및 출력 결과 포함.

### visualization_preparation

데이터 시각화를 위한 사전 도구로 두 가지 목적이 있습니다.

#### 데이터 -> 차트
분석에 필요한 데이터(.csv)와 해당 시각화 설명을 데이터에서 추출하여 최종적으로 JSON 구성 파일을 출력합니다.

#### 차트 + 인사이트 -> 차트
기존 차트와 해당 데이터 인사이트를 선택하고, 데이터 주석 형태로 차트에 추가할 데이터 인사이트를 선택하여 최종적으로 JSON 구성 파일을 생성합니다.

#### 입력
```typescript
{
  // 코드 유형: 데이터 시각화 또는 데이터 인사이트 추가
  code_type: "visualization" | "insight"
  // 최종 JSON 파일을 생성하는 데 사용되는 Python 코드
  code: string;
}
```

#### 출력
`data_visualization tool`에 사용되는 데이터 시각화를 위한 구성 파일.

## data_visualization

`visualization_preparation`의 내용을 기반으로 특정 데이터 시각화를 생성합니다.

### 입력
```typescript
{
  // 구성 파일 경로
  json_path: string;
  // 현재 목적, 데이터 시각화 또는 인사이트 주석 추가
  tool_type: "visualization" | "insight";
  // 최종 제품 png 또는 html; html은 vchart 렌더링 및 상호작용 지원
  output_type: 'png' | 'html'
  // 언어, 현재 중국어 및 영어 지원
  language: "zh" | "en"
}
```

## VMind 구성

### LLM

VMind는 지능형 차트 생성을 위해 LLM 호출이 필요합니다. 기본적으로 `config.llm["default"]` 구성을 사용합니다.

### 생성 설정

주요 구성에는 차트 크기, 테마 및 생성 방법이 포함됩니다.
### 생성 방법
기본값: png. 현재 LLM이 컨텍스트에 따라 `output_type`을 자동으로 선택하는 것을 지원합니다.

### 크기
기본 크기는 지정되지 않았습니다. HTML 출력의 경우 차트는 기본적으로 전체 페이지를 채웁니다. PNG 출력의 경우 기본값은 `1000*1000`입니다.

### 테마
기본 테마: `'light'`. VChart는 여러 테마를 지원합니다. [테마](https://www.visactor.io/vchart/guide/tutorial_docs/Theme/Theme_Extension)를 참조하세요.

## 테스트

현재, 서로 다른 난이도의
