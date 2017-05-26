#!groovy

node {
    stage ('Checkout') {
        checkout scm
    }
    stage ('Install dependencies') {
        sh 'sudo apt-get update -y'
        sh 'sudo apt-get install devscripts debhelper dh-systemd pep8 pyflakes python3-pyflakes  pyflakes python3-httpretty python3-mock python3-nose python3-coverage python3-pep8 python3-flake8 python3-hacking -y'
    }
    stage ('Build') {
        echo "Building branch: ${env.BRANCH_NAME}"
	sh 'make deb'
    }
    stage ('Flake') {
        echo 'Running flake'
        sh 'tox -e flake8'
    }
    stage ('Test') {
        echo 'Testing. py27'
        sh 'tox -e py27'
    }
    stage ('Deploying') {
        echo 'Deploying...'
    }
}

