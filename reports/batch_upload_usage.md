# Usage Instructions

## Environment Preparation

It is recommended to use Python 3.6 or higher.
Install dependencies:

```
pip install requests copr-cli copr

```

Place the `copr-cli` configuration file in the `~/.config/copr` directory. For this part, please refer [here](https://eur.openeuler.openatom.cn/api/).

Next, please ensure that Gitee access credentials are present in the environment. Modify them using the following commands:

```
export GITEE_USERNAME="your_gitee_username"
export GITEE_TOKEN="your_gitee_access_token"

```

## Usage

### View Help

```
python batch_upload_ros.py

```

If you run it without any arguments, it will output simple usage instructions by default.

### Generate Package Information

```
python batch_upload_ros.py createjson

```

The script will use the Gitee API configured above to retrieve a list of all repositories under the username and check if each repository contains the `TARGET_BRANCH` defined in the script.

> `TARGET_BRANCH`: Since my branch currently defaults to `Multi-Version_ros-jazzy_openEuler-24.03-LTS`, the script will generate the JSON based on this `TARGET_BRANCH`. If you have other branch requirements, please modify it.

If it exists, the repository's information (including `clone_url`, the inferred spec filename, etc.) is written to `packages_info.json`. Below is an example snippet:

```
...
  {
    "repo_name": "vitis_common",
    "full_name": "Sebastianlin/vitis_common",
    "clone_url": "https://gitee.com/Sebastianlin/vitis_common.git",
    "package_name": "Ros-jazzy-vitis_common",
    "spec_name": "vitis_common.spec"
  },
  ...

```

> "Inferred spec filename" refers to naming the spec file using the package name.

### Batch Upload

If you are satisfied with the generated JSON file, you can directly use the command:

```
python batch_upload_ros.py upload

```

to perform the batch upload.

## Expected Result

As shown in the image above, the repositories in the JSON file can be correctly batch uploaded.

## Existing Issues

As seen in the image above, the first letter of the package name is capitalized. I plan to fix this issue in the next step; otherwise, there are no other issues.

## Additional Notes

If you have other questions about the script or need more help, you can first check the [script](https://www.google.com/search?q=./%2520batch_upload_ros.py.py) yourself, which contains detailed comments explaining the code.

If you still have questions after reviewing the script, feel free to open an issue in this repository.