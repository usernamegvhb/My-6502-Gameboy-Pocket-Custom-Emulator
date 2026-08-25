.sign PYGBP
.ver 2
.start 0600

.label _init
  ldy #63
  ldx #7
.label _hide_loop
  lda #1
  sta $05, x
  inx
  inx
  inx
  inx
  dey
  bnz _hide_loop

  ldx #0
  lda #76
  sta $05, x

  ldx #1
  lda #68
  sta $05, x

  ldx #2
  lda #0
  sta $05, x

  ldx #3
  lda #0
  sta $05, x

.label _start
  ldx #0
  lda $F0, x
  sta $06

  lda $06
  and #1
  bez _skip_up
  ldx #1
  lda $05, x
  dea
  sta $05, x

.label _skip_up
  lda $06
  and #2
  bez _skip_down
  ldx #1
  lda $05, x
  ina
  sta $05, x

.label _skip_down
  lda $06
  and #4
  bez _skip_left
  ldx #0
  lda $05, x
  dea
  sta $05, x

.label _skip_left
  lda $06
  and #8
  bez _skip_right
  ldx #0
  lda $05, x
  ina
  sta $05, x

.label _skip_right
  jmp _start