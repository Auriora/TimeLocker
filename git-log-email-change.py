#!/usr/bin/env python3
import subprocess
import sys


def change_git_email(old_email, new_email):
    # Prepare the filter-branch command with the email replacement
    git_filter = f'''
    if [ "$GIT_COMMITTER_EMAIL" = "{old_email}" ]
    then
        export GIT_COMMITTER_EMAIL="{new_email}"
    fi
    if [ "$GIT_AUTHOR_EMAIL" = "{old_email}" ]
    then
        export GIT_AUTHOR_EMAIL="{new_email}"
    fi
    '''

    try:
        # Execute git filter-branch command
        subprocess.run([
                'git',
                'filter-branch',
                '--env-filter', git_filter,
                '--force',
                '--all'
        ], check=True)
        print(f"Successfully changed email from {old_email} to {new_email}")

    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) != 3:
        print("Usage: python change_git_email.py <old_email> <new_email>")
        print("Example: python change_git_email.py old@example.com new@example.com")
        sys.exit(1)

    old_email = sys.argv[1]
    new_email = sys.argv[2]

    # Confirm with the user
    print(f"This will change all commits from {old_email} to {new_email}")
    print("This operation will rewrite Git history!")
    response = input("Are you sure you want to continue? (y/N): ")

    if response.lower() != 'y':
        print("Operation cancelled.")
        sys.exit(0)

    change_git_email(old_email, new_email)

    print("\nNext steps:")
    print("1. Review the changes to ensure they are correct")
    print("2. If you've already pushed to a remote repository, you'll need to force push:")
    print("   git push --force origin main")
    print("   (Replace 'main' with your branch name)")
    print("\nWarning: Force pushing will rewrite history on the remote repository!")


if __name__ == "__main__":
    main()
