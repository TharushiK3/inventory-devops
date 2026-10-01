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
                // Build a Docker image tagged with this Jenkins build number.
                bat '''
                    docker build -t inventory-devops:build-%BUILD_NUMBER% .
                    if errorlevel 1 exit /b 1
                '''
            }
        }

        stage('Test') {
            steps {
                // Create a separate environment in the Jenkins workspace.
                bat '''
                    python -m venv .venv
                    if errorlevel 1 exit /b 1
                '''

                bat '''
                    .venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt
                    if errorlevel 1 exit /b 1
                '''

                // Fail if tests fail or application line coverage is below 80%.
                bat '''
                    .venv\\Scripts\\python.exe -m pytest tests -v --cov=app --cov-fail-under=80 --cov-report=term-missing --cov-report=xml:coverage.xml --junitxml=junit.xml
                    if errorlevel 1 exit /b 1
                '''
            }

            post {
                always {
                    // Publish reports even when tests fail.
                    junit testResults: 'junit.xml', allowEmptyResults: false

                    archiveArtifacts(
                        artifacts: 'coverage.xml',
                        allowEmptyArchive: true
                    )
                }
            }
        }
    }
}