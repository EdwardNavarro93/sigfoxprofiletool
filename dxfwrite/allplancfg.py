#!/usr/bin/env python
#coding:utf-8
# Purpose: create and write allplan cfg files
# Created: 24.03.2010
# Copyright (C) 2010, Manfred Moitzi
# License: MIT License

__author__ = "mozman <mozman@gmx.at>"

from .std import DXFColorIndex

allplan_default_color_table = [
    (255, 255, 255), # 0
    (  0,   0,   0), # 1
    (255, 255,   0), # 2
    (  0, 255, 255), # 3
    (  0, 255,   0), # 4
    (255,   0, 255), # 5
    (255,   0,   0), # 6
    (  0,   0, 255), # 7
    (255, 128,   0), # 8
    (240, 240, 180), # 9
    (220, 255, 100), # 10
    (200, 200,  50), # 11
    (200, 150,  50), # 12
    (200, 100,  50), # 13
    (150, 100,  50), # 14
    (130,  30, 180), # 15
    ( 45,  45,  45), # 16
    ( 59,  59,  59), # 17
    ( 73,  73,  73), # 18
    ( 87,  87,  87), # 19
    (101, 101, 101), # 20
    (115, 115, 115), # 21
    (129, 129, 129), # 22
    (143, 143, 143), # 23
    (157, 157, 157), # 24
    (171, 171, 171), # 25
    (185, 185, 185), # 26
    (199, 199, 199), # 27
    (213, 213, 213), # 28
    (227, 227, 227), # 29
    (241, 241, 241), # 30
    (250, 250, 250), # 31
    ( 80, 80 ,   0), # 32
    (110, 110,   0), # 33
    (128, 128,   0), # 34
    (179, 179,   0), # 35
    (198, 198,   0), # 36
    (217, 217,   0), # 37
    (236, 236,   0), # 38
    (245, 245,   0), # 39
    (255, 255,  28), # 40
    (255, 255,  56), # 41
    (255, 255,  84), # 42
    (255, 255, 112), # 43
    (255, 255, 140), # 44
    (255, 255, 168), # 45
    (255, 255, 196), # 46
    (255, 255, 224), # 47
    (0,  80,  80),   # 48
    (0, 110, 110),   # 49
    (0, 128, 128),   # 50
    (0, 179, 179),   # 51
    (0, 198, 198),   # 52
    (0, 217, 217),   # 53
    (0, 236, 236),   # 54
    (0, 245, 245),   # 55
    ( 28, 255, 255), # 56
    ( 56, 255, 255), # 57
    ( 84, 255, 255), # 58
    (112, 255, 255), # 59
    (140, 255, 255), # 60
    (168, 255, 255), # 61
    (196, 255, 255), # 62
    (224, 255, 255), # 63
    (0, 80 , 0), # 64
    (0, 110, 0), # 65
    (0, 128, 0), # 66
    (0, 179, 0), # 67
    (0, 198, 0), # 68
    (0, 217, 0), # 69
    (0, 236, 0), # 70
    (0, 245, 0), # 71
    ( 28, 255,  28), # 72
    ( 56, 255,  56), # 73
    ( 84, 255,  84), # 74
    (112, 255, 112), # 75
    (140, 255, 140), # 76
    (168, 255, 168), # 77
    (196, 255, 196), # 78
    (224, 255, 224), # 79
    ( 80, 0,  80),   # 80
    (110, 0, 110),   # 81
    (128, 0, 128),   # 82
    (179, 0, 179),   # 83
    (198, 0, 198),   # 84
    (217, 0, 217),   # 85
    (236, 0, 236),   # 86
    (245, 0, 245),   # 87
    (255, 28,  255), # 88
    (255, 56,  255), # 89
    (255, 84,  255), # 90
    (255, 112, 255), # 91
    (255, 140, 255), # 92
    (255, 168, 255), # 93
    (255, 196, 255), # 94
    (255, 224, 255), # 95
    (80 , 0, 0), # 96
    (110, 0, 0), # 97
    (128, 0, 0), # 98
    (179, 0, 0), # 99
    (198, 0, 0), # 100
    (217, 0, 0), # 101
    (236, 0, 0), # 102
    (245, 0, 0), # 103
    (255,  28,  28), # 104
    (255,  56,  56), # 105
    (255,  84,  84), # 106
    (255, 112, 112), # 107
    (255, 140, 140), # 108
    (255, 168, 168), # 109
    (255, 196, 196), # 110
    (255, 224, 224), # 111
    (0, 0,  80), # 112
    (0, 0, 110), # 113
    (0, 0, 128), # 114
    (0, 0, 179), # 115
    (0, 0, 198), # 116
    (0, 0, 217), # 117
    (0, 0, 236), # 118
    (0, 0, 245), # 119
    ( 28,  28, 255), # 120
    ( 56,  56, 255), # 121
    ( 84,  84, 255), # 122
    (112, 112, 255), # 123
    (140, 140, 255), # 124
    (168, 168, 255), # 125
    (196, 196, 255), # 126
    (224, 224, 255), # 127
    (120, 60, 20), # 128
    (135, 70, 20), # 129
    (150, 80, 20), # 130
    (165, 90, 20), # 131
    (180, 100, 20), # 132
    (195, 110, 20), # 133
    (210, 120, 20), # 134
    (225, 130, 20), # 135
    (240, 145, 30), # 136
    (240, 150, 40), # 137
    (240, 155, 50), # 138
    (240, 160, 60), # 139
    (240, 165, 70), # 140
    (240, 170, 80), # 141
    (240, 175, 90), # 142
    (240, 180,100), # 143
    (160, 160, 140), # 144
    (170, 170, 145), # 145
    (180, 180, 150), # 146
    (190, 190, 155), # 147
    (200, 200, 160), # 148
    (210, 210, 165), # 149
    (220, 220, 170), # 150
    (230, 230, 175), # 151
    (240, 240, 189), # 152
    (240, 240, 198), # 153
    (240, 240, 207), # 154
    (240, 240, 216), # 155
    (240, 240, 225), # 156
    (240, 240, 234), # 157
    (240, 240, 243), # 158
    (240, 240, 252), # 159
    (100, 135,  60), # 160
    (115, 150,  65), # 161
    (130, 165,  70), # 162
    (145, 180,  75), # 163
    (160, 195,  80), # 164
    (175, 210,  85), # 165
    (190, 225,  90), # 166
    (205, 240,  95), # 167
    (224, 255, 110), # 168
    (228, 255, 120), # 169
    (232, 255, 130), # 170
    (236, 255, 140), # 171
    (240, 255, 150), # 172
    (244, 255, 160), # 173
    (248, 255, 170), # 174
    (252, 255, 180), # 175
    (120, 120 ,50), # 176
    (130, 130 ,50), # 177
    (140, 140 ,50), # 178
    (150, 150 ,50), # 179
    (160, 160 ,50), # 180
    (170, 170 ,50), # 181
    (180, 180 ,50), # 182
    (190, 190 ,50), # 183
    (205, 206, 65), # 184
    (210, 212, 80), # 185
    (215, 218, 95), # 186
    (220, 224, 110), # 187
    (225, 230, 125), # 188
    (230, 236, 140), # 189
    (235, 242, 155), # 190
    (240, 248, 170), # 191
    ( 80,  70, 50), # 192
    ( 95,  80, 50), # 193
    (110,  90, 50), # 194
    (125, 100, 50), # 195
    (140, 110, 50), # 196
    (155, 120, 50), # 197
    (170, 130, 50), # 198
    (185, 140, 50), # 199
    (205, 155, 60), # 200
    (210, 160, 70), # 201
    (215, 165, 80), # 202
    (220, 170, 90), # 203
    (225, 175, 100), # 204
    (230, 180, 110), # 205
    (235, 185, 120), # 206
    (240, 190, 130), # 207
    ( 80, 20, 10), # 208
    ( 95, 30, 15), # 209
    (110, 40, 20), # 210
    (125, 50, 25), # 211
    (140, 60, 30), # 212
    (155, 70, 35), # 213
    (170, 80, 40), # 214
    (185, 90, 45), # 215
    (206, 110, 60), # 216
    (212, 120, 70), # 217
    (218, 130, 80), # 218
    (224, 140, 90), # 219
    (230, 150, 100), # 220
    (236, 160, 110), # 221
    (242, 170, 120), # 222
    (248, 180, 130), # 223
    ( 70,  20,  10), # 224
    ( 80,  30,  15), # 225
    (90, 40, 20), # 226
    (100, 50, 25), # 227
    (110, 60, 30), # 228
    (120, 70, 35), # 229
    (130, 80, 40), # 230
    (140, 90, 45), # 231
    (155, 113, 67), # 232
    (160, 126, 84), # 233
    (165, 139, 101), # 234
    (170, 152, 118), # 235
    (175, 165, 135), # 236
    (180, 178, 152), # 237
    (185, 191, 169), # 238
    (190, 204, 186), # 239
    (15, 30, 60), # 240
    (30, 30, 75), # 241
    (45, 30, 90), # 242
    (60, 30, 105), # 243
    (75, 30, 120), # 244
    (90, 30, 135), # 245
    (105, 30, 150), # 246
    (120, 30, 165), # 247
    (140, 50, 189), # 248
    (150, 70, 198), # 249
    (160, 90, 207), # 250
    (170, 110, 216), # 251
    (180, 130, 225), # 252
    (190, 150, 234), # 253
    (200, 170, 243), # 254
    (210, 190, 252), # 255
]

class AllplanColorIndex(DXFColorIndex):
    def __init__(self, user_styles=None):
        super(AllplanColorIndex, self).__init__( # Allplan 0 is a valid color index
            color_table=allplan_default_color_table, start_index=0)
