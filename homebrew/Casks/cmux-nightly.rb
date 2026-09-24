cask "cmux-nightly" do
  version :latest
  sha256 :no_check

  url "https://github.com/manaflow-ai/cmux/releases/download/nightly/cmux-nightly-macos.dmg"
  name "cmux NIGHTLY"
  desc "Nightly build of cmux; separate bundle ID, runs alongside the stable app"
  homepage "https://cmux.com"

  depends_on macos: :sonoma

  # No `binary` stanza on purpose: /opt/homebrew/bin/cmux belongs to the stable
  # cask and must keep resolving to the stable app.
  app "cmux NIGHTLY.app"

  zap trash: [
    "~/Library/Application Support/com.cmuxterm.app.nightly",
    "~/Library/Caches/com.cmuxterm.app.nightly",
    "~/Library/Preferences/com.cmuxterm.app.nightly.plist",
  ]
end
