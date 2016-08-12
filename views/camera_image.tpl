%#Bottle Template to generate HTML to display an image
<html>
  <head>
    <title>USP Agent: Camera Images</title>
    <link href="/static/style.css" rel="stylesheet" type="text/css">
  </head>
  <body>
    <p>Camera Image from {{timestamp}}</p>
    <p/>
    <img src="{{filename}}"/>
  </body>
</html>
