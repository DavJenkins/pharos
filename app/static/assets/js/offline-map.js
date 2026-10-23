/* All map, font, sprite and script requests stay on the Ark. */
(() => {
  const message = document.getElementById('message');
  try {
    const protocol = new pmtiles.Protocol();
    maplibregl.addProtocol('pmtiles', protocol.tile);
    const origin = window.location.origin;
    const map = new maplibregl.Map({container:'map',center:[-71.80,42.35],zoom:8,maxZoom:18,
      maxBounds:[[-73.51,41.23],[-69.90,42.89]],
      style:{version:8,
        glyphs:origin+'/assets/vendor/maps/protomaps-assets/fonts/{fontstack}/{range}.pbf',
        sprite:origin+'/assets/vendor/maps/protomaps-assets/sprites/v4/light',
        sources:{protomaps:{type:'vector',url:'pmtiles://'+origin+'/library-files/maps/osm/massachusetts.pmtiles',
          attribution:'<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a> · <a href="https://protomaps.com">Protomaps</a> · Natural Earth' }},
        layers:basemaps.layers('protomaps',basemaps.namedFlavor('light'),{lang:'en'})}});
    map.addControl(new maplibregl.NavigationControl());
    map.addControl(new maplibregl.ScaleControl());
    map.on('load',()=>{message.textContent='Map ready — served locally by the Ark.';});
    map.on('error',(event)=>{message.textContent='Map could not fully load. '+(event.error?.message || 'Check the archive and local viewer assets.');});
  } catch (error) { message.textContent='Map unavailable: '+error.message; }
})();
