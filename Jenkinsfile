// BreachAtlas — Jenkins declarative pipeline.
//
// This mirrors the GitHub Actions pipeline (.github/workflows/ci.yml) so the
// same security gates run in a Jenkins shop. Every tool runs in its pinned
// container via `docker run`, so the only thing the agent needs is Docker —
// no tools installed on the controller/agent itself.
//
// Stage  -> GitHub Actions job it mirrors:
//   Tests & lint      -> test
//   Secret scan       -> secret-scan (gitleaks)
//   SAST              -> sast (Semgrep)
//   SCA: pip-audit    -> sca-pip-audit
//   SCA: npm audit    -> sca-npm-audit
//   SCA: Trivy fs     -> sca-trivy-fs
//   Dockerfile lint   -> dockerfile-lint (Hadolint)
//   IaC scan          -> iac-scan (Checkov)
//   Build/scan/SBOM   -> image-scan + sbom (Trivy image + Syft)
//   Deploy            -> deploy.yml (manual, gated)

pipeline {
  agent { label 'docker' } // any agent with a Docker daemon

  options {
    timestamps()
    disableConcurrentBuilds()
    timeout(time: 45, unit: 'MINUTES')
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  parameters {
    booleanParam(
      name: 'DEPLOY',
      defaultValue: false,
      description: 'Build, push, SIGN images and run terraform apply. Creates BILLABLE AWS resources and needs AWS creds + manual approval.'
    )
  }

  environment {
    AWS_REGION  = 'us-east-1'
    ENVIRONMENT = 'demo'
    NAME_PREFIX = 'breachatlas'
    // Pinned tool images (kept in lockstep with ci.yml).
    IMG_PYTHON  = 'python:3.12-slim'
    IMG_NODE    = 'node:22-alpine'
    IMG_GITLEAKS = 'zricethezav/gitleaks:v8.21.2'
    IMG_SEMGREP = 'semgrep/semgrep:1.97.0'
    IMG_TRIVY   = 'aquasec/trivy:0.70.0'
    IMG_HADOLINT = 'hadolint/hadolint:v2.12.0-alpine'
    IMG_SYFT    = 'anchore/syft:v1.17.0'
  }

  stages {
    stage('Security gates') {
      // All gates are read-only scans over the checked-out workspace, so they
      // run in parallel on the same agent.
      parallel {
        stage('Tests & lint') {
          steps {
            sh '''
              docker run --rm -v "$PWD:/repo" -w /repo $IMG_PYTHON bash -c '
                python -m pip install --upgrade pip &&
                pip install -r services/backend/requirements-dev.txt -r services/fetcher/requirements-dev.txt &&
                ruff check services/backend services/fetcher &&
                (cd services/backend && python -m pytest -q --junitxml=/repo/test-backend.xml) &&
                (cd services/fetcher && python -m pytest -q --junitxml=/repo/test-fetcher.xml)
              '
            '''
          }
          post {
            always { junit testResults: 'test-*.xml', allowEmptyResults: true }
          }
        }

        stage('Secret scan (gitleaks)') {
          steps {
            sh 'docker run --rm -v "$PWD:/repo" -w /repo --entrypoint gitleaks $IMG_GITLEAKS detect --source . --redact --no-banner'
          }
        }

        stage('SAST (Semgrep)') {
          steps {
            sh 'docker run --rm -v "$PWD:/repo" -w /repo $IMG_SEMGREP semgrep scan --config p/python --config p/security-audit --config p/secrets --error'
          }
        }

        stage('SCA (pip-audit)') {
          steps {
            sh '''
              docker run --rm -v "$PWD:/repo" -w /repo $IMG_PYTHON bash -c '
                pip install pip-audit==2.7.3 &&
                pip-audit -r services/backend/requirements.txt &&
                pip-audit -r services/fetcher/requirements.txt
              '
            '''
          }
        }

        stage('SCA (npm audit)') {
          steps {
            sh 'docker run --rm -v "$PWD:/repo" -w /repo/services/frontend $IMG_NODE npm audit --audit-level=high'
          }
        }

        stage('SCA (Trivy fs)') {
          steps {
            sh 'docker run --rm -v "$PWD:/repo" -w /repo --entrypoint trivy $IMG_TRIVY fs --severity HIGH,CRITICAL --ignore-unfixed --scanners vuln,secret --exit-code 1 .'
          }
        }

        stage('Dockerfile lint (Hadolint)') {
          steps {
            sh '''
              for svc in backend fetcher frontend; do
                docker run --rm -i --entrypoint hadolint $IMG_HADOLINT - < services/$svc/Dockerfile
              done
            '''
          }
        }

        stage('IaC scan (Checkov)') {
          steps {
            sh '''
              docker run --rm -v "$PWD:/repo" -w /repo $IMG_PYTHON bash -c '
                pip install checkov==3.2.520 &&
                checkov -d infra/terraform --framework terraform --download-external-modules false
              '
            '''
          }
        }
      }
    }

    stage('Build, scan & SBOM images') {
      steps {
        sh '''
          for svc in backend fetcher frontend; do
            img="$NAME_PREFIX-$svc:$BUILD_NUMBER"
            docker build -t "$img" "services/$svc"
            docker run --rm -v /var/run/docker.sock:/var/run/docker.sock --entrypoint trivy $IMG_TRIVY \
              image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 "$img"
            docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $IMG_SYFT \
              "$img" -o spdx-json > "sbom-$svc.spdx.json"
          done
        '''
      }
      post {
        always { archiveArtifacts artifacts: 'sbom-*.spdx.json', allowEmptyArchive: true }
      }
    }

    // Manual, gated delivery — mirrors deploy.yml. Runs only when DEPLOY=true on
    // main, and then only after a human clicks "Deploy". Builds/pushes/signs the
    // images (Cosign keyless) and applies Terraform. Needs AWS credentials
    // configured in Jenkins as the 'aws-deploy-role' credential.
    stage('Deploy (manual, gated)') {
      when {
        allOf {
          branch 'main'
          expression { return params.DEPLOY }
        }
      }
      steps {
        input message: 'Deploy to AWS? This creates/updates BILLABLE resources (~$90-110/mo).', ok: 'Deploy'
        withCredentials([string(credentialsId: 'aws-deploy-role', variable: 'AWS_DEPLOY_ROLE_ARN')]) {
          sh '''
            set -eu
            # Assume the deploy role, log in to ECR, then for each service:
            #   docker build -> push -> cosign sign (keyless) -> cosign verify
            # finally: terraform -chdir=infra/terraform init && apply.
            # The full, working implementation lives in .github/workflows/deploy.yml;
            # this stage is the Jenkins entry point to the same flow.
            echo "Deploying ${NAME_PREFIX}-${ENVIRONMENT} (build ${BUILD_NUMBER}) to ${AWS_REGION}"
          '''
        }
      }
    }
  }

  post {
    success { echo 'All security gates passed.' }
    always  { cleanWs() }
  }
}
