" Vim syntax file
if version < 600
  syntax clear
elseif exists("b:current_syntax")
 finish
endif

if version < 600
  source <sfile>:p:h/conf.vim
else
  runtime! syntax/conf.vim
endif

syn keyword shineConfKey    tuning_file
syn keyword shineConfKey    conf_dir
syn keyword shineConfKey    lmf_dir
syn keyword shineConfKey    backend

syn keyword shineConfKey    storage_file
syn keyword shineConfKey    status_dir

syn keyword shineConfKey    log_file
syn keyword shineConfKey    log_level

syn keyword shineConfKey    color

syn keyword shineConfKey    ssh_connect_timeout
syn keyword shineConfKey    ssh_fanout
syn keyword shineConfKey    default_timeout
syn keyword shineConfKey    start_timeout
syn keyword shineConfKey    stop_timeout
syn keyword shineConfKey    status_timeout
syn keyword shineConfKey    mount_timeout
syn keyword shineConfKey    umount_timeout
syn keyword shineConfKey    set_tuning_timeout



" Define the default highlighting.
" For version 5.7 and earlier: only when not done already
" For version 5.8 and later: only when an item doesn't have highlighting yet
if version >= 508 || !exists("did_shine_syntax_inits")
  if version < 508
    let did_shine_syntax_inits = 1
    command -nargs=+ HiLink hi link <args>
  else
    command -nargs=+ HiLink hi def link <args>
  endif

  HiLink shineConfKey	Identifier
  "hi basicMathsOperator term=bold cterm=bold gui=bold

  delcommand HiLink
endif

let b:current_syntax = "shine"

" vim: ts=8
