lm.displayPointCloud = function(url){// Set up the scene, camera, and renderer as global variables.
  var scene, camera, renderer;

  // Sets up the scene.
  function init(data) {

      // Create the scene and set the scene size.
    scene = new THREE.Scene();
    var WIDTH = 800, HEIGHT = 600;

      // Create a renderer and add it to the DOM.
    renderer = new THREE.WebGLRenderer({antialias:true});
    renderer.setSize(WIDTH, HEIGHT);
    renderer.ShadowMapEnabled = true;
	var container = document.getElementById("lm-pointcloud-viewer");
	container.html("");
    container.appendChild(renderer.domElement);

    // More code goes here next...
    // Create a camera, zoom it out from the model a bit, and add it to the scene.
    // camera = new THREE.PerspectiveCamera(45, WIDTH / HEIGHT, 0.1, 20000);
    // camera.position.set(0,6,0);

	  // camera = new THREE.OrthographicCamera( WIDTH / - 2, WIDTH / 2, HEIGHT / 2, HEIGHT / - 2, 0.1, 1000 );
    camera = new THREE.PerspectiveCamera(50, WIDTH / HEIGHT, 0.1, 20000, 1);
    camera.position.x = -0;
    camera.position.y = -1000;
    camera.position.z = 1000;
    camera.lookAt(scene.position);
    this.perspective = "Orthographic";
	  scene.add(camera);
    // Create an event listener that resizes the renderer with the browser window.
    //window.addEventListener('resize', function() {
    //    var WIDTH = window.innerWidth,
    //         HEIGHT = window.innerHeight;
    //    renderer.setSize(WIDTH*5, HEIGHT*5);
    //    camera.aspect = WIDTH / HEIGHT;
    //    camera.updateProjectionMatrix();
    //});

    // Set the background color of the scene.
    //renderer.setClearColorHex(0x333F47, 1);

    // Create a light, set its position, and add it to the scene.
    var light = new THREE.PointLight(0xffffff);
    //var light = new THREE.HemisphereLight(0xffffff, 0xffffff, 0.6);
    light.position.set(-5000,0,1000);
    light.castShadow = true;
    scene.add(light);

    // Load in the mesh and add it to the scene.
    // var loader = new THREE.JSONLoader();
    // loader.load( "models/treehouse_logo.js", function(geometry){
    // var material = new THREE.MeshLambertMaterial({color: 0x55B663});
    // mesh = new THREE.Mesh(geometry, material);
    // scene.add(mesh);

    var geometry = new THREE.Geometry(); /*	NO ONE SAID ANYTHING ABOUT MATH! UGH!	*/

    console.log("loading points");
    var lines = data.split("\n");
    var vertexColors = [];
    var minInt = 99999;
    var maxInt = -99999;
    for (i = 0; i < lines.length; i++) {
      var ln = lines[i].split(" ");
        var z = parseFloat(ln[2]);
        var intensity = z;
        if (ln.length >3){
          intensity = parseFloat(ln[3]);
        }
        if ((intensity > 0) && (z > 1)){
          var vertex = new THREE.Vector3();
          vertex.x = parseFloat(ln[0]);
          vertex.y = parseFloat(ln[1]);
          vertex.z = z;
          if (minInt > intensity){
            minInt = intensity;
          }
          if (maxInt < intensity){
            maxInt = intensity;
          }
          vertexColors.push(intensity);
          geometry.vertices.push(vertex);
        }
    }
    for (var i=0; i<vertexColors.length; i++){
      var c = (vertexColors[i] - minInt) / (maxInt - minInt)
      geometry.colors.push(new THREE.Color(c, c, c));
    }
    console.log("loaded points");
    materials = new THREE.PointsMaterial({
        size: 2,
        opacity: 0.75,
        transparent: true
    });
    materials.vertexColors = true;

    // materials = new THREE.MeshBasicMaterial({ vertexColors: THREE.VertexColors });

    particles = new THREE.Points(geometry, materials);
    particles.castShadow = true;
    particles.receiveShadow = true;
    scene.add(particles);
    // Add OrbitControls so that we can pan around with the mouse.
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    console.log("all done!");
}

    // Renders the scene and updates the render as needed.
function animate() {

  // Read more about requestAnimationFrame at http://www.paulirish.com/2011/requestanimationframe-for-smart-animating/
  requestAnimationFrame(animate);

  // Render the scene.
  renderer.render(scene, camera);
  controls.update();

}

var processData = function(data){
  init(data);
  animate();

}

  $.ajax({
         type: "GET",
         url: url,
         dataType: "text",
         success: function(data) {processData(data);}
      });
}
