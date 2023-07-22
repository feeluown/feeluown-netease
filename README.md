# feeluown 网易云音乐插件

[![Build](https://github.com/feeluown/feeluown-netease/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/feeluown/feeluown-netease/actions/workflows/build.yml)
[![PyPI](https://img.shields.io/pypi/v/fuo_netease.svg)](https://pypi.python.org/pypi/fuo-netease)
[![Coverage Status](https://coveralls.io/repos/github/feeluown/feeluown-netease/badge.svg?branch=master)](https://coveralls.io/github/feeluown/feeluown-netease?branch=master)

## 安装

```sh
pip3 install fuo-netease
```

## changelog

### 0.9.7 (2023-07-22)
- 修复登录失败的问题：'NoneType' object has no attribute 'cache_get'

### 0.9.6 (2023-06-08)
- 移除对 feeluown.models 的依赖

### 0.9.5 (2023-04-27)
- 提供双语歌词

### 0.9.4 (2023-03-27)
- 提供专辑发布日期数据
- 优化登陆时错误处理

### 0.9.3 (2022-12-07)
- 修复获取每日推荐失败的问题

### 0.9.2 (2022-06-29)
- 修复加载用户名/歌单失败的问题

### 0.9.1 (2022-04-14)
- 修复歌单只能加载前 50 首的问题

### 0.9 (2022-03-30)
- 适配 FeelUOwn 最新版以提升稳定性
- 更好的支持云盘歌曲，比如上传等

### 0.8 (2021-11-06)
- 新增个人电台功能
- 移除老的 SongModel/MvModel 等，适配 library v2

### 0.7.1 (2021-06-25)
- 修复 https://github.com/feeluown/FeelUOwn/issues/474

### 0.7 (2021-06-01)
- 支持云盘歌曲
- 修复不能显示歌曲评论的问题

### 0.6 (2021-04-23)
- 适配 fuo 若干新功能
  - 平台图标
  - 支持 library current_user 接口
  - 改进对多品质音乐的支持
- 加入一个发现音乐的页面

### 0.5 (2021-01-07)
- 适配 fuo library v2，支持相似歌曲、歌曲评论

### 0.4.4 (2020-12-30)
- 修复不能搜索歌单的问题 #11
- 支持展示收藏歌手 #11
- 支持使用国外手机号登录 #14

### 0.4.3 (2020-08-21)
- 用户没有绑定手机号时，进行提醒 [bugfix](https://github.com/feeluown/FeelUOwn/issues/389)

### 0.4.2 (2020-02-08)
- 依赖 feeluown>=3.3.10
- 支持显示我的专辑收藏
- 支持每日推荐

### 0.4.1 (2020-02-08)
- 支持私人 FM，依赖 feeluown>=3.3.9

### 0.4 (2019-11-27)
- 使用 marshmallow >= 3.0
- 启用单测和质量检查，并接入 travis，

### 0.3 (2019-10-28)

- 支持获取歌手专辑
- 支持获取播放列表的所有歌曲

### 0.2 (2019-06-30)

- 适配 fuocore.models.Media 新设计
- 支持多品质音乐

### 0.1 (2019-03-18)

- 支持用户登录、歌曲搜索、歌词/歌曲/mv/歌手/专辑详情获取
