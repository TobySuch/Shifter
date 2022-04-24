# Contributing

Thanks for considering contributing to this project! I really appreciate any and all help of all kind. Please feel free to create issues for feature requests and any bugs you come across. If you want to work on some code, take a look at currently open issues for ideas of things to work on.

## Steps to contribute
1. Fork this repo
2. Create a new branch with a descriptive name for what you will be working on.
3. Install the project dependencies. Currently I'm only supporting docker so you will need an up to date version of Docker and Docker Compose to run it, but the rest of the dependencies will be installed for you. If you don't want to use docker, you should be able to install the dependencies from the `requirement.txt` files.
4. Write your code! Don't forget to write unit tests if they apply.
5. Before submitting your pull request, make sure your version of the code works. You can run the flake8 tests and the unit tests with the following command:
```
docker-compose -f docker-compose.test.yml build && docker-compose -f docker-compose.test.yml run web
```
6. Create a pull request into this repository. In your PR please leave a comment describing the changes you have made, and link to the original issue if there is one. Once the PR has been raised, Github will run the tests to ensure everything is working and then myself (or perhaps someone else in the future) will come along to review the code. If everything looks good we will merge it in.
7. We may request some changes to be made if something doesn't look quite right. If this happens, just commit and push to the same branch and it will automatically be added to the pull request. Once you have addressed all the review's contents, tag the reviewer again for them to take another look.
