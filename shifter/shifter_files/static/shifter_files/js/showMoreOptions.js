function showMoreOptions() {
    let more_options = document.getElementById("more-options")
    let show_more_options_button = document.getElementById("show-more-options")

    more_options.classList.remove("hidden")
    show_more_options_button.classList.add("hidden")
}

function hideMoreOptions() {
    let more_options = document.getElementById("more-options")
    let show_more_options_button = document.getElementById("show-more-options")

    more_options.classList.add("hidden")
    show_more_options_button.classList.remove("hidden")
}