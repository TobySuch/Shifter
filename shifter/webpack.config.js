module.exports = {
  entry: {
    flowbite: "/app/shifter/assets/js/flowbite.js",
    filepond: "/app/shifter/assets/js/filepond.js",
    cleanupexpiredfiles: "/app/shifter/assets/js/cleanup-expired-files.js",
    timezoneutils: "/app/shifter/assets/js/timezone-utils.js",
  },
  output: {
    filename: "[name]-bundle.js",
    path: "/app/shifter/static/js",
    library: "Shifter",
    libraryTarget: "var",
  },
  module: {
    rules: [
      {
        test: /\.css$/i,
        use: ["style-loader", "css-loader"],
      },
      {
        test: /\.js$/i,
        enforce: "pre",
        use: ["source-map-loader"],
      },
    ],
  },
  // Stops flowbite sourcemap missing warnings.
  ignoreWarnings: [
    function ignoreSourcemapsloaderWarnings(warning) {
      return (
        warning.module &&
        warning.module.resource.includes("flowbite") &&
        warning.details &&
        warning.details.includes("source-map-loader")
      );
    },
  ],
  // Seems to be a bug somewhere that causes builds to fail in production mode.
  // This fixes it. I believe its related to flowbite.
  optimization: {
    concatenateModules: false,
  },
};
