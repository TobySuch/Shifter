# Contributing

Thanks for considering contributing to this project! I really appreciate any and all help of any kind. Please feel free to create issues for feature requests and any bugs you come across. If you want to work on some code, take a look at the currently open issues for ideas of things to work on, although I would happily take a look at any pull requests for any changes you want to make.

## Steps to contribute

1. Fork this repo
2. Create a new branch with a descriptive name for what you will be working on.
3. Install the project dependencies. Currently, we only support Docker, so you will need an up-to-date version of Docker and Docker Compose to run it. However, the rest of the dependencies will be installed for you. If you don't want to use Docker, you should be able to install the dependencies from the `requirement.txt` and `package.json` files.
4. Write your code! Don't forget to write unit tests if they apply.
5. Before submitting your pull request, make sure your code works. You can check your linting and the unit tests with the following command:

```
docker compose -f docker/dev/docker-compose.test.yml build && docker compose -f docker/dev/docker-compose.test.yml run shifter; docker compose -f docker/dev/docker-compose.test.yml down
```

6. Create a pull request into this repository. In your PR, please leave a comment describing the changes you have made and link to the original issue if there is one. Once the PR has been raised, Github will run the tests to ensure everything is working, and then I (or someone else in the future) will review the code. If everything looks good, we will merge it in.
7. We may request some changes to be made if something doesn't look quite right. If this happens, just commit and push to the same branch, and it will automatically be added to the pull request. Once you have addressed all the review's comments, tag the reviewer again for them to take another look.
