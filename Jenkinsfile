pipeline {
    agent {
        label 'windows-docker'
    }

    options {
        disableConcurrentBuilds()
        skipStagesAfterUnstable()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {
        stage('Build') {
            steps {
                bat '''
                    docker build -t inventory-devops:build-%BUILD_NUMBER% .
                    if errorlevel 1 exit /b 1
                '''
            }
        }

        stage('Test') {
            steps {
                bat '''
                    python -m venv .venv
                    if errorlevel 1 exit /b 1
                '''

                bat '''
                    .venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt
                    if errorlevel 1 exit /b 1
                '''

                bat '''
                    .venv\\Scripts\\python.exe -m pytest tests -v --cov=app --cov-fail-under=80 --cov-report=term-missing --cov-report=xml:coverage.xml --junitxml=junit.xml
                    if errorlevel 1 exit /b 1
                '''
            }

            post {
                always {
                    junit testResults: 'junit.xml', allowEmptyResults: false

                    archiveArtifacts(
                        artifacts: 'coverage.xml',
                        allowEmptyArchive: true
                    )
                }
            }
        }

        stage('Code Quality') {
            steps {
                script {
                    def scannerHome = tool 'InventoryScanner'

                    withEnv(["SCANNER_HOME=${scannerHome}"]) {
                        withSonarQubeEnv('InventorySonarQube') {
                            bat '''
                                @echo off
                                set "SONAR_TOKEN=%SONAR_AUTH_TOKEN%"
                                call "%SCANNER_HOME%\\bin\\sonar-scanner.bat"
                                if errorlevel 1 exit /b 1
                            '''
                        }
                    }
                }
            }
        }
    }
}