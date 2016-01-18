;; -*- mode: emacs-lisp -*-
;; This file is loaded by Spacemacs at startup.
;; It must be stored in your home directory.

(defun dotspacemacs/layers ()
  "Configuration Layers declaration.
You should not put any user code in this function besides modifying the variable
values."
  (setq-default
   ;; Base distribution to use. This is a layer contained in the directory
   ;; `+distribution'. For now available distributions are `spacemacs-base'
   ;; or `spacemacs'. (default 'spacemacs)
   dotspacemacs-distribution 'spacemacs
   ;; List of additional paths where to look for configuration layers.
   ;; Paths must have a trailing slash (i.e. `~/.mycontribs/')
   dotspacemacs-configuration-layer-path '()
   ;; List of configuration layers to load. If it is the symbol `all' instead
   ;; of a list then all discovered layers will be installed.
   dotspacemacs-configuration-layers
   '(
     ;; ----------------------------------------------------------------
     ;; Example of useful layers you may want to use right away.
     ;; Uncomment some layer names and press <SPC f e R> (Vim style) or
     ;; <M-m f e R> (Emacs style) to install them.
     ;; ----------------------------------------------------------------
     ;; auto-completion
     ;; better-defaults
     syntax-checking
     emacs-lisp
     git
     python
     javascript
     auto-completion
     yaml
     markdown
     html
     eyebrowse
     deft
     (shell :variables
            shell-default-shell 'eshell
            shell-default-position 'full
            shell-enable-smart-eshell t)
     (haskell :variables
              haskell-enable-shm-support t)
     ;; (perspectives :variables
     ;;               perspective-enable-persp-projectile t)
     (org :variables
          org-enable-github-support t)
     )
   ;; List of additional packages that will be installed without being
   ;; wrapped in a layer. If you need some configuration for these
   ;; packages then consider to create a layer, you can also put the
   ;; configuration in `dotspacemacs/config'.
   dotspacemacs-additional-packages '()
   ;; A list of packages and/or extensions that will not be install and loaded.
   dotspacemacs-excluded-packages '()
   ;; If non-nil spacemacs will delete any orphan packages, i.e. packages that
   ;; are declared in a layer which is not a member of
   ;; the list `dotspacemacs-configuration-layers'. (default t)
   dotspacemacs-delete-orphan-packages t))

(defun dotspacemacs/init ()
  "Initialization function.
This function is called at the very startup of Spacemacs initialization
before layers configuration.
You should not put any user code in there besides modifying the variable
values."
  ;; This setq-default sexp is an exhaustive list of all the supported
  ;; spacemacs settings.
  (setq-default
   ;; One of `vim', `emacs' or `hybrid'. Evil is always enabled but if the
   ;; variable is `emacs' then the `holy-mode' is enabled at startup. `hybrid'
   ;; uses emacs key bindings for vim's insert mode, but otherwise leaves evil
   ;; unchanged. (default 'vim)
   dotspacemacs-editing-style 'vim
   ;; If non nil output loading progress in `*Messages*' buffer. (default nil)
   dotspacemacs-verbose-loading nil
   ;; Specify the startup banner. Default value is `official', it displays
   ;; the official spacemacs logo. An integer value is the index of text
   ;; banner, `random' chooses a random text banner in `core/banners'
   ;; directory. A string value must be a path to an image format supported
   ;; by your Emacs build.
   ;; If the value is nil then no banner is displayed. (default 'official)
   dotspacemacs-startup-banner 'official
   ;; List of items to show in the startup buffer. If nil it is disabled.
   ;; Possible values are: `recents' `bookmarks' `projects'.
   ;; (default '(recents projects))
   dotspacemacs-startup-lists '(recents projects)
   ;; List of themes, the first of the list is loaded when spacemacs starts.
   ;; Press <SPC> T n to cycle to the next theme in the list (works great
   ;; with 2 themes variants, one dark and one light)
   dotspacemacs-themes '(
                         ;; spacemacs-dark
                         ;; spacemacs-light
                         ;; solarized-light
                         ;; solarized-dark
                         ;; leuven
                         monokai
                         ;; zenburn
                         )
   ;; If non nil the cursor color matches the state color.
   dotspacemacs-colorize-cursor-according-to-state t
   ;; Default font. `powerline-scale' allows to quickly tweak the mode-line
   ;; size to make separators look not too crappy.
   dotspacemacs-default-font '("Source Code Pro"
                               :size 13
                               :weight normal
                               :width normal
                               :powerline-scale 1.1)
   ;; The leader key
   dotspacemacs-leader-key "SPC"
   ;; The leader key accessible in `emacs state' and `insert state'
   ;; (default "M-m")
   dotspacemacs-emacs-leader-key "M-m"
   ;; Major mode leader key is a shortcut key which is the equivalent of
   ;; pressing `<leader> m`. Set it to `nil` to disable it. (default ",")
   dotspacemacs-major-mode-leader-key ","
   ;; Major mode leader key accessible in `emacs state' and `insert state'.
   ;; (default "C-M-m)
   dotspacemacs-major-mode-emacs-leader-key "C-M-m"
   ;; The command key used for Evil commands (ex-commands) and
   ;; Emacs commands (M-x).
   ;; By default the command key is `:' so ex-commands are executed like in Vim
   ;; with `:' and Emacs commands are executed with `<leader> :'.
   dotspacemacs-command-key ";"
   ;; If non nil `Y' is remapped to `y$'. (default t)
   dotspacemacs-remap-Y-to-y$ t
   ;; Location where to auto-save files. Possible values are `original' to
   ;; auto-save the file in-place, `cache' to auto-save the file to another
   ;; file stored in the cache directory and `nil' to disable auto-saving.
   ;; (default 'cache)
   dotspacemacs-auto-save-file-location 'cache
   ;; If non nil then `ido' replaces `helm' for some commands. For now only
   ;; `find-files' (SPC f f), `find-spacemacs-file' (SPC f e s), and
   ;; `find-contrib-file' (SPC f e c) are replaced. (default nil)
   dotspacemacs-use-ido nil
   ;; If non nil, `helm' will try to miminimize the space it uses. (default nil)
   dotspacemacs-helm-resize t
   ;; if non nil, the helm header is hidden when there is only one source.
   ;; (default nil)
   dotspacemacs-helm-no-header nil
   ;; define the position to display `helm', options are `bottom', `top',
   ;; `left', or `right'. (default 'bottom)
   dotspacemacs-helm-position 'right
   ;; If non nil the paste micro-state is enabled. When enabled pressing `p`
   ;; several times cycle between the kill ring content. (default nil)
   dotspacemacs-enable-paste-micro-state nil
   ;; Which-key delay in seconds. The which-key buffer is the popup listing
   ;; the commands bound to the current keystroke sequence. (default 0.4)
   dotspacemacs-which-key-delay 0.4
   ;; Which-key frame position. Possible values are `right', `bottom' and
   ;; `right-then-bottom'. right-then-bottom tries to display the frame to the
   ;; right; if there is insufficient space it displays it at the bottom.
   ;; (default 'bottom)
   dotspacemacs-which-key-position 'bottom
   ;; If non nil a progress bar is displayed when spacemacs is loading. This
   ;; may increase the boot time on some systems and emacs builds, set it to
   ;; nil to boost the loading time. (default t)
   dotspacemacs-loading-progress-bar t
   ;; If non nil the frame is fullscreen when Emacs starts up. (default nil)
   ;; (Emacs 24.4+ only)
   dotspacemacs-fullscreen-at-startup nil
   ;; If non nil `spacemacs/toggle-fullscreen' will not use native fullscreen.
   ;; Use to disable fullscreen animations in OSX. (default nil)
   dotspacemacs-fullscreen-use-non-native nil
   ;; If non nil the frame is maximized when Emacs starts up.
   ;; Takes effect only if `dotspacemacs-fullscreen-at-startup' is nil.
   ;; (default nil) (Emacs 24.4+ only)
   dotspacemacs-maximized-at-startup nil
   ;; A value from the range (0..100), in increasing opacity, which describes
   ;; the transparency level of a frame when it's active or selected.
   ;; Transparency can be toggled through `toggle-transparency'. (default 90)
   dotspacemacs-active-transparency 90
   ;; A value from the range (0..100), in increasing opacity, which describes
   ;; the transparency level of a frame when it's inactive or deselected.
   ;; Transparency can be toggled through `toggle-transparency'. (default 90)
   dotspacemacs-inactive-transparency 90
   ;; If non nil unicode symbols are displayed in the mode line. (default t)
   dotspacemacs-mode-line-unicode-symbols t
   ;; If non nil smooth scrolling (native-scrolling) is enabled. Smooth
   ;; scrolling overrides the default behavior of Emacs which recenters the
   ;; point when it reaches the top or bottom of the screen. (default t)
   dotspacemacs-smooth-scrolling nil
   ;; If non-nil smartparens-strict-mode will be enabled in programming modes.
   ;; (default nil)
   dotspacemacs-smartparens-strict-mode t
   ;; Select a scope to highlight delimiters. Possible values are `any',
   ;; `current', `all' or `nil'. Default is `all' (highlight any scope and
   ;; emphasis the current one). (default 'all)
   dotspacemacs-highlight-delimiters 'all
   ;; If non nil advises quit functions to keep server open when quitting.
   ;; (default nil)
   dotspacemacs-persistent-server nil
   ;; List of search tool executable names. Spacemacs uses the first installed
   ;; tool of the list. Supported tools are `ag', `pt', `ack' and `grep'.
   ;; (default '("ag" "pt" "ack" "grep"))
   dotspacemacs-search-tools '("ag" "pt" "ack" "grep")
   ;; The default package repository used if no explicit repository has been
   ;; specified with an installed package.
   ;; Not used for now. (default nil)
   dotspacemacs-default-package-repository nil
   ))

(defun dotspacemacs/user-init ()
  "Initialization function for user code.
It is called immediately after `dotspacemacs/init'.  You are free to put any
user code."
  (setq git-magit-status-fullscreen t)
  (advice-add 'spacemacs/persp-switch-project :before #'aron/add-project-marks))

(defun aron/add-project-marks () 
  (interactive)
  (projectile-clear-known-projects) 
  (let* ((markdir (expand-file-name "~/marks/"))
         (marks (directory-files markdir))
         (add-project (lambda (filename)
                        (let ((long-filename (file-truename (concat markdir filename))))
                          (projectile-add-known-project long-filename)))))
    (mapcar add-project marks)))

(defun aron/activate-virtualenv-based-on-project ()
  (interactive)
  (when (equal major-mode 'python-mode)
    (let ((proj (projectile-project-name)))
      (pyvenv-workon proj)
      (message "activated virtualenv: %s" proj))))

(defun aron/magit-status-buffer-switch-function (buffer)
  (delete-other-windows))

(defun aron/set-shell-pop-dir-on-projectile-root ()
  (interactive)
  (let ((dir (if (projectile-project-p)
                 (projectile-project-root)
               (helm-current-directory))))
    (setq shell-pop-default-directory dir)))

(defun dotspacemacs/user-config ()
  "Configuration function for user code.
 This function is called at the very end of Spacemacs initialization after
layers configuration. You are free to put any user code."
  (bind-key "C-;" 'evil-normal-state evil-insert-state-map)
  (bind-key "C-;" 'evil-normal-state evil-visual-state-map)
  ;; evil-lisp-state is not loaded during startup, so only bind to its keymap
  ;; once it's loaded.
  (with-eval-after-load 'evil-lisp-state
    (bind-key "C-;" 'evil-normal-state evil-lisp-state-map))
  (bind-key "C-r" 'evil-search-backward evil-normal-state-map)
  (bind-key "C-x C-x" 'spacemacs/default-pop-shell)
  (bind-key "C-c C-c" 'eval-defun)
  (evil-leader/set-key "." 'find-tag)
  (evil-leader/set-key "," 'pop-tag-mark)
  (evil-leader/set-key "o" 'spacemacs/workspaces-micro-state)
  (evil-leader/set-key "|" 'split-window-right-and-focus)
  (evil-leader/set-key "-" 'split-window-below-and-focus)
  (evil-leader/set-key "p g" 'spacemacs/helm-project-do-ag)
  (evil-leader/set-key "[" 'spacemacs/toggle-maximize-buffer)

  (setq haskell-interactive-popup-errors nil)

  ;; keybindings and setup for org mode
  (with-eval-after-load 'org
    (bind-key "M-i" 'org-insert-heading-after-current org-mode-map)

    ;; agenda files for work and personal are added by default
    (setq org-default-notes-file "~/notes/capture.org")
    (add-to-list 'org-agenda-files "~/notes/capture.org")
    (add-to-list 'org-agenda-files "~/notes/personal.org")
    (add-to-list 'org-agenda-files "~/notes/work.org")

    ;; org setup
    (setq org-refile-targets '((org-agenda-files :maxlevel . 2)))
    (setq org-todo-keywords
          '((sequence "TODO(t)" "WAIT(w@/!)" "|" "DONE(d!)" "CANCELED(c@)")))
    (add-to-list 'org-modules 'habits)

    ;; deft setup
    (setq deft-directory "~/notes")

    ;; I only want to see a day as the default for org-agenda
    (setq org-agenda-span 'day)

    ;; sync our notes directory everyday
    (run-at-time "10:30am" 43200 (lambda () (call-process "~/notes/push.sh"))) ; 43200 sec == 12 hours
    )

  (evil-leader/set-key "a a" 'org-agenda-list)
  (evil-leader/set-key "a o i" 'org-clock-in-last)
  (spacemacs/toggle-mode-line-org-clock-on)

  ;; helm ag fuzzy searching!
  (setq helm-ag-fuzzy-match t)

  ;; always pop to the projec root, if available
  (advice-add 'spacemacs/default-pop-shell :before #'aron/set-shell-pop-dir-on-projectile-root)

  ;; add magit status mode to modes that start in emacs state
  (advice-add 'magit-status :after #'aron/magit-status-buffer-switch-function)

  ;; (add-to-list 'evil-emacs-state-modes 'magit-status-mode)
  ;; (debug)
  ;; (setq evil-evilified-state-modes (delete 'magit-status-mode evil-evilified-state-modes))

  ;; switch virtualenvs when we switch projects
  (add-hook 'find-file-hook 'aron/activate-virtualenv-based-on-project)

  ;; fix some things with haskell mode
  (evil-define-key 'insert haskell-mode-map "<RET>" 'shm/newline-indent)

  ;; see dired when switching to new project
  (setq projectile-switch-project-action 'projectile-dired)

  ;; turn off those goddamn GTK tooltips -- they're messing with jump mode
  (setq x-gtk-use-system-tooltips nil)

  ;; turn on syntax checking
  (add-hook 'prog-mode-hook 'spacemacs/toggle-syntax-checking-on)

  ;; turn off haskell indentation mode, since we use shm
  ;; (add-hook 'haskell-mode-hook (lambda () (haskell-indentation-mode -1)))
  ;; turn on haskell indentation mode
  (add-hook 'haskell-mode-hook 'turn-on-haskell-indentation)
  (add-hook 'haskell-mode-hook 'interactive-haskell-mode)

  ;; ;; add news source to gnus
  ;; (setq gnus-secondary-select-methods)

  ;; add anaconda jump points to the marker stack
  (advice-add 'anaconda-mode-find-definitions :before #'xref-push-marker-stack)
  (advice-add 'anaconda-mode-find-assignments :before #'xref-push-marker-stack)
  (advice-add 'anaconda-mode-find-references :before #'xref-push-marker-stack)

  ;; turn on the indent guide
  (spacemacs/toggle-indent-guide-globally-on)
  )

;; Do not write anything past this comment. This is where Emacs will
;; auto-generate custom variable definitions.
(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(ansi-color-faces-vector
   [default default default italic underline success warning error])
 '(ansi-color-names-vector
   ["black" "red3" "ForestGreen" "yellow3" "blue" "magenta3" "DeepSkyBlue" "gray50"])
 '(compilation-message-face (quote default))
 '(cua-global-mark-cursor-color "#2aa198")
 '(cua-normal-cursor-color "#839496")
 '(cua-overwrite-cursor-color "#b58900")
 '(cua-read-only-cursor-color "#859900")
 '(fci-rule-color "#073642" t)
 '(highlight-changes-colors (quote ("#d33682" "#6c71c4")))
 '(highlight-symbol-colors
   (--map
    (solarized-color-blend it "#002b36" 0.25)
    (quote
     ("#b58900" "#2aa198" "#dc322f" "#6c71c4" "#859900" "#cb4b16" "#268bd2"))))
 '(highlight-symbol-foreground-color "#93a1a1")
 '(highlight-tail-colors
   (quote
    (("#073642" . 0)
     ("#546E00" . 20)
     ("#00736F" . 30)
     ("#00629D" . 50)
     ("#7B6000" . 60)
     ("#8B2C02" . 70)
     ("#93115C" . 85)
     ("#073642" . 100))))
 '(hl-bg-colors
   (quote
    ("#7B6000" "#8B2C02" "#990A1B" "#93115C" "#3F4D91" "#00629D" "#00736F" "#546E00")))
 '(hl-fg-colors
   (quote
    ("#002b36" "#002b36" "#002b36" "#002b36" "#002b36" "#002b36" "#002b36" "#002b36")))
 '(magit-diff-use-overlays nil)
 '(package-selected-packages
   (quote
    (org-toodledo flycheck-pos-tip anzu request evil xterm-color ws-butler spaceline restart-emacs persp-mode orgit lorem-ipsum hl-todo help-fns+ helm-flx helm-company evil-mc evil-magit evil-lisp-state evil-indent-plus auto-compile ace-jump-helm-line bind-map deft popup bind-key dash auto-complete yasnippet diminish package-build avy highlight haskell-mode helm helm-core multiple-cursors json-reformat projectile eyebrowse web-mode tagedit slim-mode scss-mode sass-mode less-css-mode jade-mode helm-css-scss haml-mode emmet-mode company-web stickyfunc-enhance srefactor mmm-mode markdown-toc markdown-mode gh-md shell-pop multi-term eshell-prompt-extras esh-help yaml-mode persp-projectile helm-c-yasnippet company-tern company-statistics company-quickhelp company-ghc company-cabal company-anaconda company auto-yasnippet ac-ispell web-beautify tern shm json-mode js2-refactor js2-mode js-doc hindent haskell-snippets ghc flycheck-haskell flycheck coffee-mode cmm-mode toc-org org-repo-todo org-present org-pomodoro org-plus-contrib org-bullets htmlize gnuplot evil-org pyvenv pytest pyenv-mode pip-requirements hy-mode helm-pydoc cython-mode anaconda-mode monokai-theme paradox magit-gitflow magit git-commit window-numbering which-key volatile-highlights vi-tilde-fringe use-package spray spacemacs-theme smooth-scrolling smeargle smartparens s rainbow-delimiters quelpa powerline popwin pcre2el page-break-lines open-junk-file neotree move-text macrostep linum-relative leuven-theme info+ indent-guide ido-vertical-mode hungry-delete highlight-parentheses highlight-numbers highlight-indentation helm-themes helm-swoop helm-projectile helm-mode-manager helm-make helm-gitignore helm-descbinds helm-ag google-translate golden-ratio gitconfig-mode gitattributes-mode git-timemachine git-messenger flx-ido fill-column-indicator fancy-battery expand-region exec-path-from-shell evil-visualstar evil-tutor evil-surround evil-search-highlight-persist evil-numbers evil-nerd-commenter evil-matchit evil-leader evil-jumper evil-indent-textobject evil-iedit-state evil-exchange evil-escape evil-args evil-anzu eval-sexp-fu elisp-slime-nav define-word clean-aindent-mode buffer-move auto-highlight-symbol auto-dictionary aggressive-indent adaptive-wrap ace-window ace-link)))
 '(pos-tip-background-color "#073642")
 '(pos-tip-foreground-color "#93a1a1")
 '(smartrep-mode-line-active-bg (solarized-color-blend "#859900" "#073642" 0.2))
 '(term-default-bg-color "#002b36")
 '(term-default-fg-color "#839496")
 '(truncate-lines t)
 '(vc-annotate-background nil)
 '(vc-annotate-color-map
   (quote
    ((20 . "#dc322f")
     (40 . "#c85d17")
     (60 . "#be730b")
     (80 . "#b58900")
     (100 . "#a58e00")
     (120 . "#9d9100")
     (140 . "#959300")
     (160 . "#8d9600")
     (180 . "#859900")
     (200 . "#669b32")
     (220 . "#579d4c")
     (240 . "#489e65")
     (260 . "#399f7e")
     (280 . "#2aa198")
     (300 . "#2898af")
     (320 . "#2793ba")
     (340 . "#268fc6")
     (360 . "#268bd2"))))
 '(vc-annotate-very-old-color nil)
 '(weechat-color-list
   (quote
    (unspecified "#002b36" "#073642" "#990A1B" "#dc322f" "#546E00" "#859900" "#7B6000" "#b58900" "#00629D" "#268bd2" "#93115C" "#d33682" "#00736F" "#2aa198" "#839496" "#657b83"))))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(company-tooltip-common ((t (:inherit company-tooltip :weight bold :underline nil))))
 '(company-tooltip-common-selection ((t (:inherit company-tooltip-selection :weight bold :underline nil)))))
