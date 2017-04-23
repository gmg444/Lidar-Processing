// ----------------------------------------------------------------------------
// Starting module for lidar maps - sets up global namespace, loads modules,
// and acts as controller, mediating echange of information between modules.
// ----------------------------------------------------------------------------

// Set up a slot for our objects in the global namespace ("window")
var lm = window.lm || {};

// After the document is loaded according to jquery, set up our code.
$(document).ready(function(){
  $("#lm-modal-about").modal();
  $("#lm-about-link").on("click", function(){$("#lm-modal-about").modal(); });

  // Set up configuration information - put anything that is likely to change
  // after the site is up and running here, so we don't have to go fishing through.
  // the code to make changes.
  var config = {
    ajaxUrl: "http://localhost:8080/",
    startingLat: 42.3251,
    startingLon: -72.6412,
    startingZoom: 13
  };

  // Set up starting state - this is a dictionary into which we can put
  // any information that needs to be passed between modules, without creating
  // global variables.
  var state = { };

  // This is the function the map will call when anything in the state changes.
  // Note that the map can update the UI, zoom or pan or do anything else without
  // changing the state.  State changes are just for those changes that need to
  // be reflected in actions taken by other modules.  Currently these are
  // called explicitly but we can change this to be generic if we have many modules
  // It's likely more maintainable to centrlize the inter-module communication here
  // instead of spreading around module references, which gets complicated fase
  // ******* TODO -add callbacks for modules that need to share data *******

  // Each module loaded after this one should have put their objects into the lm
  // global variable, and can be initialized here.

  lm.lmap.init(config, state);

  $("#lm-area-details").css("display", "none");
  $("#lm-available-layers").css("display", "none");
});

/* $(document).ready(function() {
  $("#elev_items").hide();
  $("#forest_items").hide();
  $("a#elev_click").click(function() {
    $("#elev_items").toggle("fast");
  });
  $("a#forest_click").click(function() {
    $("#forest_items").toggle("fast");
  });
}); */
