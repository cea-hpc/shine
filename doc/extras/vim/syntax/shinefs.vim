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

syn keyword shineFSKey              description
syn keyword shineFSKey              failover
syn keyword shineFSKey              fs_name
syn keyword shineFSKey              mdt_mkfs_options
syn keyword shineFSKey              mdt_mount_options
syn keyword shineFSKey              mdt_mount_path
syn keyword shineFSKey              mdt_format_params
syn keyword shineFSKey              mount_options
syn keyword shineFSKey              mount_path
syn keyword shineFSKey              mgt_mkfs_options
syn keyword shineFSKey              mgt_mount_options
syn keyword shineFSKey              mgt_mount_path
syn keyword shineFSKey              mgt_format_params
syn keyword shineFSKey              nid_map contained
syn keyword shineFSKey              ost_mkfs_options
syn keyword shineFSKey              ost_mount_options
syn keyword shineFSKey              ost_mount_path
syn keyword shineFSKey              ost_format_params
syn keyword shineFSKey              quota
syn keyword shineFSKey              quota_type
syn keyword shineFSKey              quota_iunit
syn keyword shineFSKey              quota_bunit
syn keyword shineFSKey              quota_btune
syn keyword shineFSKey              quota_itune
syn keyword shineFSKey              stripe_count
syn keyword shineFSKey              stripe_size
syn keyword shineFSKey              mgt
syn keyword shineFSKey              mdt
syn keyword shineFSKey              ost
syn keyword shineFSKey              client

syn match shineVariable             /\$\(fs_name\|index\)/

syn match shineTargetTagKey         /\(tag\|node\|dev\|jdev\|index\|ha_node\|mode\|group\)=/me=e-1

syn match  shineComment            " #.*"ms=s+1 contained

syn match shineHostPattern          /=[^ @]\+/ms=s+1 contained
syn match shineNidPattern           /=[^ ]\+@[^ ]\+/ms=s+1 contained
syn keyword shineNidKey            nodes contained
syn keyword shineNidKey            nids contained
syn match shineNidMap              /^nid_map: *[^ ]\+ *[^ ]\+@[^ ]\+.*/ contains=shineFSKey,shineNidKey,shineHostPattern,shineNidPattern,shineComment


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

  HiLink shineComment        Comment
  HiLink shineFSKey          Identifier
  HiLink shineNidKey         Identifier
  HiLink shineTargetTagKey   Identifier
  HiLink shineTargetNodeKey  Identifier
  HiLink shineTargetDevKey   Identifier
  HiLink shineTargetJdevKey  Identifier
  HiLink shineTargetSizeKey  Identifier
  HiLink shineTargetJsizeKey Identifier
  HiLink shineTargetIndexKey Identifier

"  HiLink shineNidMap        Label
  HiLink shineHostPattern    Type
  HiLink shineNidPattern     String
  HiLink shineVariable       PreProc

  delcommand HiLink
endif

let b:current_syntax = "shinefs"

" vim: ts=8
