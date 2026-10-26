/* All map, font, sprite and script requests stay on the Ark. */
(() => {
  const message = document.getElementById('message');
  try {
    const protocol = new pmtiles.Protocol();
    maplibregl.addProtocol('pmtiles', protocol.tile);
    const origin = window.location.origin;
    const map = new maplibregl.Map({container:'map',center:[-96,38],zoom:3.5,maxZoom:18,
      bounds:[[-125,24],[-66,50]],fitBoundsOptions:{padding:24},
      style:{version:8,
        glyphs:origin+'/assets/vendor/maps/protomaps-assets/fonts/{fontstack}/{range}.pbf',
        sprite:origin+'/assets/vendor/maps/protomaps-assets/sprites/v4/light',
        sources:{protomaps:{type:'vector',url:'pmtiles://'+origin+'/library-files/maps/osm/usa.pmtiles',
          attribution:'<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a> · <a href="https://protomaps.com">Protomaps</a> · Natural Earth' }},
        layers:basemaps.layers('protomaps',basemaps.namedFlavor('light'),{lang:'en'})}});
    const regions={conus:[[-125,24],[-66,50]],alaska:[[-188,51],[-129,72]],hawaii:[[-179,18],[-154,29]]};
    for(const button of document.querySelectorAll('[data-map-region]'))button.addEventListener('click',()=>{map.fitBounds(regions[button.dataset.mapRegion],{padding:24,duration:500});});
    map.addControl(new maplibregl.NavigationControl());
    map.addControl(new maplibregl.ScaleControl());
    map.on('load',()=>{message.textContent='Map ready — served locally by the Ark.';});
    map.on('error',(event)=>{message.textContent='Map could not fully load. '+(event.error?.message || 'Check the archive and local viewer assets.');});
  } catch (error) { message.textContent='Map unavailable: '+error.message; }
})();
