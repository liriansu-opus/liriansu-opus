cask "tflint" do
  arch arm: "arm64", intel: "amd64"

  version "0.64.0"
  sha256 arm:   "2496e9cb3d24992d553b45e7c87a0fdc9449ca975233876247a9bfeda857e6c0",
         intel: "0f3a9fd17526014646a2dfc3f9122f7b4161abe3d6b0f0f03f9014483ddf4d19"

  url "https://github.com/terraform-linters/tflint/releases/download/v#{version}/tflint_darwin_#{arch}.zip"
  name "TFLint"
  desc "Pluggable Terraform linter"
  homepage "https://github.com/terraform-linters/tflint"

  # Upstream's own cask is GoReleaser-generated and skips livecheck; this one
  # tracks releases so `brew livecheck tflint` reports a new version to bump to.
  livecheck do
    url :url
    strategy :github_latest
  end

  binary "tflint"

  # The release zip is unsigned, so the staged binary carries a quarantine
  # attribute that Gatekeeper refuses to run from the terminal.
  postflight_steps do
    run "/usr/bin/xattr", args: ["-dr", "com.apple.quarantine", "{{staged_path}}/tflint"]
  end

  zap trash: "~/.tflint.d"
end
