pipeline {
    agent any

    environment {
        IMAGE_NAME = 'laptop-recommender'
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out source code...'
            }
        }

        stage('Lint and Test') {
            steps {
                echo 'Building test stage and executing tests/linters inside Docker...'
                // Build the test target; if any linter or test fails, this step fails the build.
                sh 'docker build --target test -t ${IMAGE_NAME}:test .'
            }
        }

        stage('Build Production Image') {
            steps {
                echo 'Building the final minimal production Docker image...'
                sh 'docker build --target production -t ${IMAGE_NAME}:latest .'
            }
        }
    }

    post {
        always {
            echo 'Pipeline finished. Cleaning up build artifacts...'
            // Clean up dangling images to prevent running out of disk space on the agent
            sh 'docker image prune -f'
        }
        success {
            echo 'Build and test pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed. Please check the linter or test logs above.'
        }
    }
}
