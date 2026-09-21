# AWS EC2 배포 준비

이 프로젝트의 GitHub Actions는 테스트와 Docker 이미지 빌드가 성공한 뒤 `main` 브랜치를
EC2에 배포합니다. 수동 실행 시에는 `deploy` 입력을 선택해야 배포 Job이 실행됩니다.

## EC2 준비

Docker Engine과 Docker Compose Plugin이 설치된 EC2에서 최초 한 번 다음을 실행합니다.

```bash
mkdir -p ~/mini-agent-01-llm
cd ~/mini-agent-01-llm
nano .env.docker
chmod 600 .env.docker
```

`.env.docker.example`을 기준으로 Provider Key와 모델을 입력합니다. `.env.docker`는
GitHub Actions가 복사하거나 로그에 출력하지 않으며, 서버에 미리 만든 파일을 계속
사용합니다. `.env`는 컨테이너가 아닌 로컬 Python 개발 실행에만 사용합니다.

Ollama를 같은 EC2 호스트에서 실행할 경우 기본값인
`http://host.docker.internal:11434`를 사용할 수 있습니다. 별도 서버에서 실행한다면
`OLLAMA_BASE_URL`을 해당 주소로 변경합니다.

## GitHub production Environment

Repository의 `Settings -> Environments`에서 `production` Environment를 만들고 다음
Secret을 등록합니다.

| Secret | 값 |
| --- | --- |
| `AWS_HOST` | EC2 Public DNS 또는 IP |
| `AWS_USER` | 예: `ec2-user` |
| `AWS_SSH_PRIVATE_KEY` | 배포용 Private Key 전체 |
| `AWS_SSH_KNOWN_HOSTS` | 관리자가 확인한 EC2 known_hosts 한 줄 |

운영 환경에서는 SSH 22번 포트를 전체 인터넷에 개방하지 말고 VPN, Bastion, SSM 또는
self-hosted Runner 등 조직의 접근 정책을 사용합니다. 외부에는 Frontend 8501 포트만
공개하고 Backend 8000 포트는 보안 그룹에서 차단하는 구성을 권장합니다.

## 확인

```bash
cd ~/mini-agent-01-llm
docker compose ps
docker compose logs --tail=100 backend frontend
curl --fail http://127.0.0.1:8000/health
```
