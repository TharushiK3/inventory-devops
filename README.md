\# Velvet Stock — Inventory DevOps



An inventory management application built with Python, Flask and SQLite, with a seven-stage Jenkins pipeline.



\## Application features



\- Create, edit and delete products.

\- Track stock and highlight low-stock products.

\- Record sales and calculate revenue in LKR.

\- Reject sales when there is insufficient stock.

\- Preserve the original sale price in sales history.

\- Prevent deletion of products with recorded sales.

\- Validate product and sale inputs.

\- Protect POST forms using session-based CSRF tokens.

\- Provide a database-aware `/health` endpoint.



\## Requirements



\- Windows with Git and Python 3.13.

\- Docker Desktop running with Linux containers and WSL 2.

\- Jenkins with a Windows agent labelled `windows-docker`.

\- SonarQube Community Build for code analysis.



Commands below use Windows PowerShell unless stated otherwise.



\## Clone and run locally



Access to this private repository is required.



```powershell

git clone https://github.com/TharushiK3/inventory-devops.git

cd inventory-devops



python -m venv .venv

.\\.venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt

.\\.venv\\Scripts\\python.exe run.py

```



Keep the terminal open while the application runs.



Application: http://127.0.0.1:5000  

Health endpoint: http://127.0.0.1:5000/health



The local database is created automatically in `instance`.



\## Automated tests



Run from the repository folder in another PowerShell window:



```powershell

.\\.venv\\Scripts\\python.exe -m pytest tests -v --cov=app --cov-fail-under=80 --cov-report=term-missing --cov-report=xml:coverage.xml --junitxml=junit.xml

```



The verified assessment build passed 28 tests with approximately 87% application coverage. The pipeline requires at least 80% coverage.



\## Security scans



```powershell

.\\.venv\\Scripts\\python.exe -m pip install -r requirements-security.txt

.\\.venv\\Scripts\\python.exe -m bandit -r app run.py

.\\.venv\\Scripts\\python.exe -m pip\_audit -r requirements.txt

```



Bandit checks Python code for potential security issues. pip-audit checks application dependencies against known vulnerability advisories.



The verified scans reported no Bandit findings and no known dependency vulnerabilities. Results can change as vulnerability advisories are updated.



\## Run with Docker



```powershell

docker build -t inventory-devops:local .



docker run -d --name inventory-local -p 127.0.0.1:5001:5000 --mount source=inventory-local-data,target=/app/instance -e APP\_ENV=container-test -e APP\_VERSION=local inventory-devops:local

```



Application: http://127.0.0.1:5001  

Health endpoint: http://127.0.0.1:5001/health



If `inventory-local` already exists, start it with:



```powershell

docker start inventory-local

```



Check the container and application:



```powershell

docker ps --filter name=inventory-local



.\\.venv\\Scripts\\python.exe -u scripts\\check\_health.py --url http://127.0.0.1:5001 --environment container-test --version local

```



The health script checks database connectivity, environment, version and the inventory homepage.



\## Jenkins configuration



\### Windows agent



Create and connect a Jenkins agent with:



\- Label: `windows-docker`

\- One executor.

\- A writable workspace.

\- Access to Git, Python and the running Docker Desktop daemon.



Run the agent using the connection command provided by Jenkins. Keep its terminal open if it runs interactively.



\### Plugins and tools



Install the Jenkins plugins needed for:



\- Pipeline.

\- Git.

\- Credentials Binding.

\- JUnit.

\- SonarQube Scanner.



Configure these names exactly, because the Jenkinsfile references them:



| Jenkins setting | Name |

|---|---|

| SonarQube server | `InventorySonarQube` |

| SonarQube Scanner tool | `InventoryScanner` |



For this setup, SonarQube is accessible from the Windows agent at:



```text

http://localhost:9000

```



Create the SonarQube project with key `inventory-devops`. Analysis settings are stored in `sonar-project.properties`.



The scanner waits for the SonarQube quality gate. A failed gate stops the pipeline.



\### Credentials



Create credentials with Global scope:



| Credential ID | Kind | Purpose |

|---|---|---|

| `github-inventory-read` | Username with password | Private GitHub checkout; use a GitHub access token as the password |

| `sonarqube-inventory-token` | Secret text | SonarQube analysis token |

| `inventory-staging-secret` | Secret text | Stable staging Flask secret key |

| `inventory-production-secret` | Secret text | Stable production Flask secret key |



Use different randomly generated secret keys for staging and production.



Select `sonarqube-inventory-token` as the authentication credential for `InventorySonarQube`.



Keep credential values out of source control.



\### Pipeline job



Create a Pipeline job with:



\- Definition: Pipeline script from SCM.

\- SCM: Git.

\- Repository: `https://github.com/TharushiK3/inventory-devops.git`

\- Credentials: the private repository checkout credential.

\- Branch: `\*/main`

\- Script path: `Jenkinsfile`



Run the first build manually to load the pipeline configuration.



The Jenkinsfile uses `pollSCM('H/5 \* \* \* \*')` to check for repository changes approximately every five minutes. A detected change triggers a build automatically.



\## Seven pipeline stages



| Stage | Action |

|---|---|

| Build | Build `inventory-devops:build-<BUILD\_NUMBER>` |

| Test | Run pytest, enforce minimum coverage and publish test results |

| Code Quality | Analyse with SonarQube and enforce its quality gate |

| Security | Run Bandit and pip-audit and archive JSON reports |

| Deploy | Deploy staging and verify health, environment, version and homepage |

| Release | Deploy the same image to production and verify it |

| Monitoring and Alerting | Start monitoring services and check fresh successful probes for both environments |



Concurrent builds are disabled. Failed checks prevent later stages from running.



Reports are available under the Jenkins build's artifacts. Test results also appear in Jenkins' test results view.



\## Deployment environments



| Environment | Application URL | Compose file |

|---|---|---|

| Staging | http://127.0.0.1:5002 | `compose.staging.yaml` |

| Production | http://127.0.0.1:5003 | `compose.production.yaml` |



Jenkins supplies the build number and environment credentials during deployment.



Both environments use the same image built in the Build stage. Each has its own persistent database volume and secret key.



The `/health` response includes the environment and Jenkins build number so the deployed version can be verified.



These are separate local demonstration environments on one Docker host. The production environment is accessible on localhost.



\## Monitoring and alerting



The monitoring stack contains:



\- Prometheus for collecting probe metrics and evaluating alert rules.

\- Blackbox Exporter for checking application health endpoints.

\- Alertmanager for routing firing and resolved notifications.

\- A local alert inbox for recording notifications.



Staging and production must be deployed before starting monitoring because monitoring uses their Docker networks.



```powershell

docker compose -p inventory-monitoring -f compose.monitoring.yaml up -d

```



| Service | URL |

|---|---|

| Prometheus | http://localhost:9090 |

| Alertmanager | http://localhost:9093 |

| Alert inbox | http://localhost:9094/notifications |



In Prometheus, execute:



```promql

probe\_success{job="inventory-health"}

```



Both staging and production should return `1`.



Run the monitoring verification script:



```powershell

.\\.venv\\Scripts\\python.exe -u scripts\\check\_monitoring.py

```



It checks service readiness and recent successful probes for both environments, then writes `reports/monitoring.json`.



\### Verify alert delivery



For a controlled staging outage:



```powershell

docker stop inventory-staging

```



Wait approximately 60–90 seconds, then inspect Prometheus alerts and the alert inbox. A staging unhealthy notification should show `firing`.



Restore staging:



```powershell

docker start inventory-staging

```



Wait for the probe to recover and the next notification. The inbox should record `resolved`.



Finally, execute the probe query again and confirm both environments return `1`.



Alert notifications are delivered to the local inbox. The outage and recovery test was performed manually; the pipeline automatically checks monitoring readiness and healthy probes.



\## Verified assessment evidence



Jenkins build #12 completed all seven stages successfully and was triggered by an SCM change.



Evidence includes:



\- Successful pipeline overview and full console output.

\- 28 passing tests and the coverage report.

\- SonarQube quality gate results.

\- Bandit and dependency audit reports.

\- Staging and production health responses for version 12.

\- Successful probes for both environments.

\- Firing and resolved staging alert notifications.

\- A recorded inventory sale and rejected overselling attempt.



A SonarQube CSRF finding was reviewed and marked False Positive with an explanation of the custom session-token validation. Other findings should be assessed separately.



\## Project structure



\- `app/` — Flask application, database, services, routes and interface.

\- `tests/` — automated application tests.

\- `scripts/` — deployment and monitoring verification.

\- `monitoring/` — monitoring configuration and alert inbox.

\- `Dockerfile` — application container image.

\- `Jenkinsfile` — seven-stage pipeline.

\- `compose.staging.yaml` — staging deployment.

\- `compose.production.yaml` — production deployment.

\- `compose.monitoring.yaml` — monitoring services.

\- `sonar-project.properties` — SonarQube analysis configuration.

