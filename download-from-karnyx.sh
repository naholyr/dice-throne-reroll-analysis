heroes="alchemist artificer barbarian black_panther black_widow captain_marvel cursed_pirate cyclops deadpool doctor_strange druid duelist forgemaster gambit gunslinger headless_horseman huntress iceman jean_grey krampus loki monk moon_elf mystic_brawler necromancer ninja paladin pale_lady psylocke pyromancer raveness rogue samurai santa scarlet_witch seraph shadow_thief spider-man storm sun_elf tactician thor treant vampire_lord wolverine"

if [ -z "$KARNYX_SESSION" ]; then
  echo "Set KARNYX_SESSION"
  exit 1
fi

DST_DIR="karnyx/heroes"
mkdir -p "$DST_DIR"
for hero in $heroes; do
  echo "${hero}..."
  curl --url "https://karnyx.app/heroes/$hero" \
    -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
    -H 'accept-language: fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7' \
    -H 'cache-control: max-age=0' \
    -b "karnyx_session=$KARNYX_SESSION" \
    -H 'priority: u=0, i' \
    -H 'referer: https://karnyx.app/heroes' \
    -H 'sec-ch-ua: "Google Chrome";v="153", "Not_A Brand";v="8", "Chromium";v="153"' \
    -H 'sec-ch-ua-mobile: ?0' \
    -H 'sec-ch-ua-platform: "macOS"' \
    -H 'sec-fetch-dest: document' \
    -H 'sec-fetch-mode: navigate' \
    -H 'sec-fetch-site: same-origin' \
    -H 'sec-fetch-user: ?1' \
    -H 'upgrade-insecure-requests: 1' \
    -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36' \
  > "$DST_DIR/$hero.html"
  echo "Saved to $DST_DIR/$hero.html"
  sleep $((RANDOM/3000+3))
done
