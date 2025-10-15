# GEN-4-ESS-BMO-Lab
Code base for GUI and Spectrometer control for ESS system BMO Lab Boston University

# Get Started
First, follow this [guide](https://docs.google.com/document/d/1FLaeKsOsEHwRYacJV5ZzHZxENfK67Uf_gcZY0pdiOOk/edit?tab=t.0#heading=h.jh40iydazfo4).

Then, once you are done and on the desktop of the Raspberry Pi:

1. Open a new terminal
```sh
sudo raspi-config
```
Under the options shows, navigate to `Interface Options`:
1. → SPI → Enable
2. → Serial Port -> Would you like a login shell to be accesible over serial  → No → Would you like the serial port hardware ot be enabled → Yes
3. Exit and reboot
