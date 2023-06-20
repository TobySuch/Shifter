module.exports = {
  entry:{
    flowbite: '/app/shifter/assets/js/flowbite.js',
    filepond: '/app/shifter/assets/js/filepond.js',
  },
  output: {
    filename: '[name]-bundle.js',
    path: '/app/shifter/static/js',
    library: 'ShifterFilepond',
    libraryTarget: 'var'
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
};