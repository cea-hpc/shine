"
" Installed As: vim/ftdetect/shine.vim
"
au BufNewFile,BufRead *shine.conf               setlocal filetype=shine
au BufNewFile,BufRead /etc/shine/models/*       setlocal filetype=shinefs
au BufNewFile,BufRead /var/cache/shine/conf/*   setlocal filetype=shinefs

