#!groovy

// Update git status.
def setBuildStatus(context, message, state) {
    step([
        $class: "GitHubCommitStatusSetter",
       // reposSource: [$class: "ManuallyEnteredRepositorySource", url: "https://github.com/blackboxsw/cloud-init"],
        contextSource: [$class: "ManuallyEnteredCommitContextSource", context: context],
        errorHandlers: [[$class: "ChangingBuildStatusErrorHandler", result: "UNSTABLE"]],
        statusResultSource: [$class: "ConditionalStatusResultSource", results: [[
            $class: "AnyBuildResult", message: message, state: state]] ]
    ]);
}

node {
    stage ('Checkout') {
        checkout scm
    }
    stage ('Build') {
        sh 'sudo apt-get update -y'
        sh 'sudo apt-get install devscripts debhelper dh-systemd pep8 pyflakes python3-pyflakes  pyflakes python3-httpretty python3-mock python3-nose python3-coverage python3-pep8 python3-flake8 python3-hacking -y'
        context = "jenkins/builddeb"
        setBuildStatus(context, "pending", "PENDING")
        echo "Building branch: ${env.BRANCH_NAME}"
	sh 'make deb'
        setBuildStatus(context, "Build complete", "SUCCESS")
    }
    stage ('Deploying') {
        echo 'Deploying...'
    }
}

