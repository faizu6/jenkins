pipeline {
    agent any
    stages {
        stage('Back-end') {
            agent {
                docker { 
                    image "faizu6/ansible-img1:4"
                    args "--user root --privileged"
                    
                }
            }
            steps {
                sh '''
                ansible-playbook ec2-Jenkins/tasks/main.yml -e Name=dev
                '''
            }
        }
    }
}
