import base64
import logging
import tempfile
import os
from shutil import copyfile
from subprocess import run
from sys import argv, exit

from git import Repo
from git.exc import GitCommandError

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    deployment_repo_url = os.getenv('INPUT_DEPLOYMENT_REPO_URL', None)
    deployment_repo_branch = os.getenv('INPUT_DEPLOYMENT_REPO_BRANCH', None)
    kustomization_path = os.getenv('INPUT_KUSTOMIZATION_PATH', None)
    deploy_key = os.getenv('INPUT_DEPLOY_KEY', None)
    git_user_name = os.getenv('INPUT_GIT_USER_NAME', None)
    git_user_email = os.getenv('INPUT_GIT_USER_EMAIL', None)

    error = False
    if deployment_repo_url == None:
        error = True
        logging.error('missing required input: `deployment_repo_url`')

    if deployment_repo_branch == None:
        error = True
        logging.error('missing required input: `deployment_repo_branch`')

    if kustomization_path == None:
        error = True
        logging.error('missing required input: `kustomization_path`')

    if deploy_key == None:
        error = True
        logging.error('missing required input: `deploy_key`')

    if git_user_name == None:
        error = True
        logging.error('missing required input: `git_user_name`')

    if git_user_email == None:
        error = True
        logging.error('missing required input: `git_user_email`')

    if error:
        exit(1)

    ssh_dir = os.path.expanduser('~/.ssh')
    git_ssh_identity_file = os.path.join(ssh_dir, 'id_rsa')
    known_hosts_file = os.path.join(os.path.dirname(__file__), 'known_hosts')

    os.makedirs(ssh_dir, mode=0x600, exist_ok=True)

    with open(os.open(git_ssh_identity_file, os.O_CREAT | os.O_WRONLY, 0o600), 'w') as id_rsa:
        id_rsa.write(base64.standard_b64decode(deploy_key).decode("utf-8"))

    with tempfile.TemporaryDirectory() as deployment_repo_path:
        repo = Repo.init(deployment_repo_path)
        repo.git.update_environment(
            GIT_SSH_COMMAND=f'ssh -i {git_ssh_identity_file} -o UserKnownHostsFile={known_hosts_file}')

        try:
            repo.delete_remote('origin')
        except GitCommandError:
            pass
        finally:
            repo.create_remote('origin', deployment_repo_url)

        try:
            repo.git.fetch('origin')
            repo.git.checkout(f'origin/{deployment_repo_branch}')
            repo.git.reset('--hard', f'origin/{deployment_repo_branch}')

            cmd = ['kustomize', 'edit', 'set', 'image', *argv[1:]]
            cwd = os.path.join(deployment_repo_path, kustomization_path)
            krun = run(cmd, capture_output=True, cwd=cwd)
            if krun.returncode != 0:
                logging.info(krun.args)
                logging.error(krun.stderr.strip().decode("UTF-8"))
                exit(krun.returncode)
            logging.info(repo.git.diff())

            repo.git.add(cwd)
            logging.info(repo.git.status())

            repo.git.config('user.name', git_user_name)
            repo.git.config('user.email', git_user_email)

            changes = []
            for arg in argv[1:]:
                changes.append(f' * {arg}')
            commit_message = 'Update kustomize images\n\n' + \
                '\n'.join(changes) + '\n'

            repo.git.commit('-m', commit_message)

            repo.git.push('origin', f'HEAD:{deployment_repo_branch}')
        except GitCommandError as e:
            logging.error(e)
            exit(1)
