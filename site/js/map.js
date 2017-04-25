// When the file is loaded it creates a new object in the lm namepace representing the map.
// Loading this via the jquery."when" function.  The new keyword here creates a new instance
// of the function, with a newly-created value of "this", which means it functions more like
// a normal class in other languages, where multiple instances of the class can be created.
// There are many opinions on how best to to this - see this discussion for example:
// http://stackoverflow.com/questions/9782379/deathmatch-self-executing-anonymous-function-vs-new-function
lm.lmap =  new function () {
  // "this" refers to the current function.  Since we need to access it from
  // other functions, which also have their own "this", we need to save it
  // in a local variable.
  var that = this;
  var map = null;
  var geoJsonLayer = null;
  var coverageLayer = null;
  var editingLayer = null;
  var currentSelectedLayer = null;
  var drawingNow = false;
  var drawControl = null;
  var selectMode = false;

  // We keep these variables private inside this curent "closure" scope.
  // using "this.ini" let's us access init() from outside this module, as
  // long as we have a reference to "this".
  this.init = function(cfg, state){
    that.state = state;
    that.ajaxUrl = cfg.ajaxUrl;

    // L is a global used by leaflet.  We can create the new leaflet map
    // by passing in the div id into which we want to display the map.
    var mapLayer = L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}.png', {
        minZoom: 5, maxZoom: 19
    });
    var imageLayer = L.tileLayer('http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}.png', {
        minZoom: 5, maxZoom: 19
    });
    map = L.map('map');
    map.setView([cfg.startingLat, cfg.startingLon], cfg.startingZoom);
    L.control.layers({"Map": mapLayer, "Satellite": imageLayer}).addTo(map);
    mapLayer.addTo(map);
    // When the user clicks on the map, we want to take some action.
    map.on("click", function(e){
      if (selectMode && !drawingNow){
          $.get( that.ajaxUrl + "/town_data?lat=" + e.latlng.lat + "&lon=" + e.latlng.lng, displayTownData, dataType="json");
      }
    });

    $("#lm-available-layers input:radio").on("change", selectLayer);
    $("#lm-select-area").on("change", selectArea)

    $.get( that.ajaxUrl + "/completed_jobs", displayCompletedJobs, dataType="json");
    map.on("mousemove", displayMapInfo);
  };

  var selectArea = function(e){
    var selectedId = e.target.value;
    clearUserPolygons();
    if (selectedId == -1){
      setUpDraw();
      selectMode = true;
      coverageLayer = L.geoJson(coverage, {
        style: {
          "color": "#F99",
          "fillColor": "#999",
          "weight": 1,
          "fillOpacity": 0.3,
          "opacity": 0.7
        },
        onEachFeature: function(feature, layer) {
          layer.on('click', function(e) {
            map.fitBounds(e.target.getBounds());
            layer.off('click');
          });
        }
      });
      coverageLayer.addTo(map);
      map.fitBounds(coverageLayer.getBounds());
      $("#lm-available-layers").css("display", "none");
    }
    else if(selectedId == 0){
      selectMode = false;
      map.removeLayer(coverageLayer);
      map.removeControl(drawControl);
      $("#lm-available-layers").css("display", "none");
    }
    else{
      $("#lm-available-layers").css("display", "block");
      $("input:radio:first").prop("checked", true).trigger("change");
      var job_id = $("#lm-select-area").val();
      $("#lm-dem-link").attr("href", "output/" + job_id.toString() + "_mosaic_dem.tif");
      $("#lm-dsm-link").attr("href", "output/" + job_id.toString() + "_mosaic_dsm.tif");
      $("#lm-chm-link").attr("href", "output/" + job_id.toString() + "_mosaic_height.tif");
    }
  };

  var displayCompletedJobs = function(response){
      $("#lm-select-area").empty();
      $("#lm-select-area").append($("<option></option>")
                  .attr("value", 0)
                  .text("Available maps"));
      $("#lm-select-area").append($("<option></option>")
                  .attr("value", -1)
                  .text("Select a new area to process"));
      if (response.data && (response.data.length > 0)){
        for (var i=0; i<response.data.length; i++){
          $("#lm-select-area").append($("<option></option>")
                    .attr("value", response.data[i].job_id)
                    .text(response.data[i].description));
        }
      }
  };

 var displayMapInfo = function(e){
   $("#lm-mouse_status").html(
     "lat: " + e.latlng.lat.toFixed(3).toString() +
     "; lng:" + e.latlng.lng.toFixed(3).toString() +
     "; zoom:" + map.getZoom().toString()
   );
  };

  var selectLayer = function(e){
     clearUserPolygons();
      if (currentSelectedLayer){
          map.removeLayer(currentSelectedLayer);
      }
      var job_id = $("#lm-select-area").val();
      var layerType = $(e.currentTarget).attr("id");
      var url = "output/" + job_id.toString() + "_mosaic_" + layerType + ".json";
      var color = "#A36";
      var fillColor = "#3A6"
      var width = 1;
      if (layerType == "bldgs"){
        color = "#36A";
        fillColor = "#A63"
      }
      if (layerType == "contours"){
        color = "#A36";
        width = 2;
      }
      $.getJSON(url,function(data){
        // add GeoJSON layer to the map once the file is loaded
        currentSelectedLayer = L.geoJson(data, {
         style: {
             "color": color,
             "fillColor": fillColor,
             "weight": width,
             "fillOpacity": 0.8,
             "opacity": 0.7
           }
         });
        currentSelectedLayer.addTo(map);
        map.fitBounds(currentSelectedLayer.getBounds());
      });
  };

  var clearUserPolygons = function(){
    if (geoJsonLayer){
        map.removeLayer(geoJsonLayer);
    }
    if (editingLayer){
        map.removeLayer(editingLayer);
    }
  };

  var setUpDraw = function(){
    // ****************************************************************
    // Adding draw controls
    // ****************************************************************
    // Initialize the FeatureGroup to store editable layers
    var drawnItems = new L.FeatureGroup().addTo(map);
    if (drawControl){
        map.removeControl(drawControl);
    }
    drawControl = new L.Control.Draw({
        draw: {
            position: 'topleft',
            polygon: {
                allowIntersection: false, // Restricts shapes to simple polygons
                drawError: {
                    color: '#990000', // Color the shape will turn when intersects
                    message: '<strong>Polygon cannot intersect itself.</strong>' // Message that will show when intersect
                },
                shapeOptions: {
                    color: '#000000'
                },
                selectedPathOptions: {
                    maintainColor: true,
                    opacity: 0.3
                }
            },
            polyline: false,
            rectangle: false,
            circle: false,
            marker: false
        },
        edit: {
            featureGroup: drawnItems,
            remove: true
        }
    }).addTo(map);

    var updateDrawing = function(layer){
        editingLayer = layer;
        var poly = editingLayer.toGeoJSON();
        map.fitBounds(editingLayer.getBounds());
        $.get( that.ajaxUrl + "/polygon_data?coords=" + JSON.stringify(poly["geometry"]["coordinates"]), displayPolygonData, dataType="json");
    };

    map.on('draw:created', function (e) {
        drawingNow = false;
        updateDrawing(e.layer);
        $(".leaflet-draw-edit-edit").css("display", "block");
    });

    map.on('draw:drawstart', function () {
        drawingNow = true;
        if (geoJsonLayer){
          map.removeLayer(geoJsonLayer);
        }
        $(".leaflet-clickable").attr("fill", "#000000");
        $(".leaflet-draw-actions a").css("color", "rgb(255,255,255)");
    });

    map.on('draw:editstart', function () {
        drawingNow = true;
        $(".leaflet-draw-actions a").css("color", "rgb(255,255,255)");
    });

    map.on('draw:editstop', function () {
        drawingNow = false;
        updateDrawing(editingLayer);
    });

    // Adjust the leaflet draw controls styling here.
    $(".leaflet-draw-edit-edit").css("display", "none");
  };

  var displayPolygonData = function(response){
    clearUserPolygons();
    status = "Not yet processed"
    if (response.data.numTiles == 0){
      status = "Not available";
    }
    if (response.data.polyGeoJson){
      geoJsonLayer = L.geoJson($.parseJSON(response.data.polyGeoJson),
      {
       style: {
         "color": "#99F",
         "fillColor": "#F99",
         "weight": 2,
         "fillOpacity": 0.3,
         "opacity": 0.7
       }
      }).addTo(map);
      map.fitBounds(geoJsonLayer.getBounds());
    }

    if (response.data.townName){
      displayAreaDetails("Custom area within " + response.data.townName + ", " + response.data.stateName,
        status, response.data.numTiles, response.data.townArea, true, response.data.polyWkt);
    }
  };

  var displayTownData = function(response){
    clearUserPolygons();
    status = "Not yet processed"
    if (response.data.numTiles == 0){
      status = "Not available";
    }
    geoJsonLayer = L.geoJson($.parseJSON(response.data.polyGeoJson), {
      style: {
        "color": "#99F",
        "fillColor": "#F99",
        "weight": 2,
        "fillOpacity": 0.3,
        "opacity": 0.7
      }
    }).addTo(map);
    map.fitBounds(geoJsonLayer.getBounds());
    displayAreaDetails(response.data.townName + ", " + response.data.stateName,
      status, response.data.numTiles, response.data.townArea,
      true, response.data.polyWkt);
  };

  var refreshStatus = function(job_id) {
    $.get( that.ajaxUrl + "/job_status?job_id=" + job_id.toString(),
      displayJobStatus, dataType="json");
  };

  var displayJobStatus = function(response){
    $("#lm-area-status").html(response.data.description);
    if (response.data.description.indexOf('complete') == -1)
      setTimeout(refreshStatus, 2000, response.data.job_id);
    else
      $.get( that.ajaxUrl + "/completed_jobs", displayCompletedJobs, dataType="json");
  };

  var displayJobStarted = function(response){
    alert("Job successfully started!");
    $("#lm-area-status").html("In progress");
    var job_id = response.data.job_id;
    refreshStatus(job_id);
  };

  var displayAreaDetails = function(areaName, status, numTiles, area, showButton, wkt){
    $("#lm-start-processing").css("display", "none");
    $("#lm-area-details").css("display", "block");
    $("#lm-area-name").html(areaName);
    if (numTiles > 50){
      $("#lm-area-status").html("The selected area is too large to process. " +
        "Please select another.");
        $("#lm-area-processing-time").html("");
    }
    else{
      $("#lm-area-status").html(status);
      $("#lm-area-processing-time").html((numTiles / 39.0).toFixed(2) + " hours");
      $("#lm-area-processing-area").html(area.toFixed(1) +  "km^2");

      if (showButton){
        $("#lm-start-processing").css("display", "block");
        $("#lm-start-job").off("click").on("click", function(){
            $.get( that.ajaxUrl + "/start_job?description=" + areaName + "&poly_wkt=" + wkt,
               displayJobStarted, dataType="json");
            $("#lm-start-processing").css("display", "none");
        });
      }
      $("#lm-start-processing").off("click").on("click", function(){
          $("#lm-modal-dialog .modal-body").html("Do you want to process this area?");
          $("#lm-modal-dialog .modal-title").html("Launch Process");
          $("#lm-modal-dialog").modal();
      });
    }
  };

  this.update = function(newState){
    console.log("Example updated");
    that.state = newState;
    console.log(that.state);
  };
};
