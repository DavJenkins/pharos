/* All map, font, sprite and script requests stay on the Ark. */
(() => {
  const message = document.getElementById('message');
  try {
    const protocol = new pmtiles.Protocol();
    maplibregl.addProtocol('pmtiles', protocol.tile);
    const origin = window.location.origin;
    const caribbean = new URLSearchParams(window.location.search).get('collection') === 'caribbean';
    const archive = caribbean ? '/library-files/maps/osm/caribbean.pmtiles' : '/library-files/maps/osm/usa.pmtiles';
    if(caribbean){
      document.querySelector('h1').textContent='Caribbean offline street map';
      document.getElementById('map-coverage').textContent='Caribbean islands, Bahamas and adjoining coasts · OpenStreetMap data: October 22, 2026';
      document.getElementById('map-download').href=archive;
      document.querySelector('.map-regions').innerHTML='<button type="button" data-map-region="caribbean">Caribbean</button> <button type="button" data-map-region="sxm">Sint Maarten / Saint-Martin</button> <button type="button" data-map-region="usvi">USVI / BVI</button> <button type="button" data-map-region="puertorico">Puerto Rico</button> <button type="button" data-map-region="bahamas">Bahamas</button>';
    }

    const map = new maplibregl.Map({container:'map',center:[-96,38],zoom:3.5,maxZoom:18,
      bounds:caribbean ? [[-89,9],[-58,28]] : [[-125,24],[-66,50]],fitBoundsOptions:{padding:24},
      style:{version:8,
        glyphs:origin+'/assets/vendor/maps/protomaps-assets/fonts/{fontstack}/{range}.pbf',
        sprite:origin+'/assets/vendor/maps/protomaps-assets/sprites/v4/light',
        sources:{protomaps:{type:'vector',url:'pmtiles://'+origin+archive,
          attribution:'<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a> · <a href="https://protomaps.com">Protomaps</a> · Natural Earth' }},
        layers:basemaps.layers('protomaps',basemaps.namedFlavor('light'),{lang:'en'})}});
    const regions={caribbean:[[-89,9],[-58,28]],sxm:[[-63.19,17.99],[-62.95,18.14]],usvi:[[-65.12,17.62],[-64.2,18.8]],puertorico:[[-67.4,17.8],[-65.2,18.6]],bahamas:[[-80.6,20.8],[-72.5,27.6]],conus:[[-125,24],[-66,50]],alaska:[[-188,51],[-129,72]],hawaii:[[-179,18],[-154,29]]};
    for(const button of document.querySelectorAll('[data-map-region]'))button.addEventListener('click',()=>{map.fitBounds(regions[button.dataset.mapRegion],{padding:24,duration:500});});
    map.addControl(new maplibregl.NavigationControl());
    map.addControl(new maplibregl.ScaleControl());
    map.on('load',()=>{message.textContent='Map ready — served locally by the Ark.';});
    map.on('error',(event)=>{message.textContent='Map could not fully load. '+(event.error?.message || 'Check the archive and local viewer assets.');});
  } catch (error) { message.textContent='Map unavailable: '+error.message; }
})();
