# Build Instructions
These instructions are to document the build process for creating a new version of the image to push to the image repository of choice. This is not intended to be a guide for building the image for an end user, or even a developer. This is intended to be a guide for the person who is responsible for building the image and pushing it to the image repository. If you are looking to build the project from scratch, check the [README file](/README.md)

## Pre-build Instructions
1. Update the version number in the `package.json` and `package-lock.json` files. Commit these changes to the repository.
2. Ensure you are logged into the image repository you are pushing to. For GHCR, generate a PAT token using [these instructions](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic) and then login using [these instructions](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#authenticating-with-a-personal-access-token-classic).


## Building The Image
```bash
export APP_VERSION=<version number>

# Build for latest tag for single architecture
docker build -f docker/Dockerfile --build-arg="APP_VERSION=$APP_VERSION" -t shifter:latest -t ghcr.io/tobysuch/shifter:latest -t ghcr.io/tobysuch/shifter:$APP_VERSION .
docker push ghcr.io/tobysuch/shifter:latest
docker push ghcr.io/tobysuch/shifter:$APP_VERSION

# Build for latest tag for multiple architectures
docker buildx create --name shifterbuilder --use --bootstrap
docker buildx build --file docker/Dockerfile --platform linux/amd64,linux/arm64 --build-arg="APP_VERSION=$APP_VERSION" --tag ghcr.io/tobysuch/shifter:$APP_VERSION --tag ghcr.io/tobysuch/shifter:latest --push .
```

## Notes
 - The `docker buildx` commands are only required if you are building for multiple architectures. If you are only building for a single architecture, you can use the `docker build` commands.
 - You can build release candidates by appending `-rc<number>` to the version number. For example, `1.0.0-rc1`. Make sure to remove the latest tag from the build command so others are not updated to the release candidate version.