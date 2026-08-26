User units for the nightly refresh (run on the machine that holds the repo and can ssh to dronesclub):

```bash
mkdir -p ~/.config/systemd/user
ln -sf ~/src/climate/contrib/systemd/climate-nightly.{service,timer} ~/src/climate/contrib/systemd/climate-weekly-us.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now climate-nightly.timer climate-weekly-us.timer
loginctl enable-linger "$USER"      # keep user timers running without a login session
systemctl --user list-timers        # check
journalctl --user -u climate-nightly.service -n 50
```
