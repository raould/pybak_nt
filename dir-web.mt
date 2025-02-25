<html>
<body>

<!-- sub dirs -->
<ul>
% for d in dirs:
  <li>${d}</li>
% endfor
</ul>

<!-- files -->
<ul>
% for ft in files:
  <li><a href="${ft['aka_url']}">${ft['item_name']}</a></li>
% endfor
</ul>

<!-- thumbs -->
<div>
% for tt in thumbs:
<a href="${tt['aka_url']}"><img src="${tt['thumb_src']}"></a></a>
% endfor
</div>

</body>
</html>
