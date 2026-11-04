"""Print-scale card mounting target for the private recipient setup sheet."""
import base64
from pathlib import Path

def hardware_notes():
    return ('<section class="recipient-hardware" style="break-before:page"><h2>Hardware</h2>'
      '<h3>Tested reference</h3><ul><li>Raspberry Pi 4 Model B, 2 GB RAM.</li>'
      '<li>CanaKit 3.5 A USB-C power supply.</li><li>MazerPi ventilated case, cooling fan and heatsinks.</li>'
      '<li>This edition: supplied 128 GB microSD with an 80 GiB system-card library.</li></ul>'
      '<h3>Recommended choices</h3><p>A Pi 4 Model B with 4 GB or 8 GB RAM gives more headroom; the tested 2 GB board works. '
      'Use a reliable Pi 4 USB-C power supply (official specification: 5 V / 3 A minimum), a sound power cable and cooling. '
      'No monitor, keyboard or mouse is required for browser setup.</p>'
      '<h3>Optional longer-range Wi-Fi</h3><p>A Linux-supported USB Wi-Fi adapter with an external antenna and access-point mode can improve hotspot range. '
      'To use it for that purpose, select it as the hotspot adapter under Wi-Fi or Hotspot → Wi-Fi adapter assignment. '
      'Merely plugging it in does not assign it to the hotspot. Range depends on the adapter, antenna, placement and surroundings. '
      'The built-in Wi-Fi can then serve optional upstream access and provides fallback when the preferred USB radio is absent.</p>'
      '<h3>Optional expansion</h3><p>An external USB content drive adds capacity. Use a properly powered USB hub if peripherals need additional power. '
      'Ethernet provides optional network/internet access. Neither an external drive nor internet access is required for this populated edition.</p>'
      '<p>Reference: <a href="https://www.raspberrypi.com/products/raspberry-pi-4-model-b/">Raspberry Pi 4 Model B</a>.</p></section>')

def card_mount(root=Path('/')):
    logo=root/'opt/dataark/app/static/assets/pharos-data-ark-clean.png'
    if not logo.is_file():
        logo=Path(__file__).resolve().parents[1]/'static/assets/pharos-data-ark-clean.png'
    image='data:image/png;base64,'+base64.b64encode(logo.read_bytes()).decode()
    # SVG coordinates are millimetres: the card envelope is exactly 11 x 15 mm.
    return ('<figure class="card-mount" style="margin:20px auto;text-align:center;break-inside:avoid">'
        '<svg xmlns="http://www.w3.org/2000/svg" width="70mm" height="70mm" viewBox="0 0 70 70" role="img" aria-label="Actual-size microSD outline inside a Pharos Data Ark circle">'
        '<circle cx="35" cy="35" r="33" fill="none" stroke="#806522" stroke-width=".4"/>'
        '<image href="'+image+'" x="10" y="10" width="50" height="20.3" preserveAspectRatio="xMidYMid meet"/>'
        '<path transform="translate(29.5 36)" d="M 1.3 0 H 11 V 6.4 L 9.8 7.9 V 13.5 H 11 V 15 H 0 V 1.3 Z" fill="none" stroke="#203e54" stroke-width=".2"/>'
        '</svg></figure>')
