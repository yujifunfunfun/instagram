from django.shortcuts import render, redirect
from django.views.generic import View
from django.conf import settings
from datetime import datetime, date
from django.utils.timezone import localtime
from .models import Insight, Post
import requests
import json
import math
import pandas as pd


def get_credentials():
    credentials = {}
    credentials['access_token'] = settings.ACCESS_TOKEN
    credentials['instagram_account_id'] = settings.INSTAGRAM_ACCOUNT_ID
    credentials['graph_domain'] = 'https://graph.facebook.com/'
    credentials['graph_version'] = 'v8.0'
    credentials['endpoint_base'] = credentials['graph_domain'] + credentials['graph_version'] + '/'
    credentials['ig_username'] = '_ysae_ti_ekat_'
    return credentials


def call_api(url, endpoint_params=''):
    if endpoint_params:
        data = requests.get(url, endpoint_params)
    else:
        data = requests.get(url)

    response = {}
    response['json_data'] = json.loads(data.content)
    return response


def get_account_info(params):
    endpoint_params = {}
    endpoint_params['fields'] = 'business_discovery.username(' + params['ig_username'] + '){\
        username,profile_picture_url,follows_count,followers_count,media_count,\
        media.limit(10){comments_count,like_count,caption,media_url,permalink,timestamp,media_type,\
        children{media_url,media_type}}}'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['instagram_account_id']
    return call_api(url, endpoint_params)


def get_media_insights(params):
    # エンドポイント
    # https://graph.facebook.com/{graph-api-version}/{ig-media-id}/insights?metric={metric}&access_token={access-token}

    endpoint_params = {}
    # エンゲージメント、インプレッション、リーチ、保存情報取得
    endpoint_params['metric'] = 'engagement,impressions,reach,saved'
    endpoint_params['access_token'] = params['access_token']
    url = params['endpoint_base'] + params['media_id'] + '/insights'
    return call_api(url, endpoint_params)


class IndexView(View):
    def get(self, request, *args, **kwargs):
        params = get_credentials()
        account_response = get_account_info(params)
        business_discovery = account_response['json_data']['business_discovery']
        account_data = {
            'profile_picture_url': business_discovery['profile_picture_url'],
            'username': business_discovery['username'],
            'followers_count': business_discovery['followers_count'],
            'follows_count': business_discovery['follows_count'],
            'media_count': business_discovery['media_count'],
        }
        today = date.today()

        obj, created = Insight.objects.update_or_create(
            label=today,
            defaults={
                'follower': business_discovery['followers_count'],
                'follows': business_discovery['follows_count']
            }
        )

        media_insight_data = Insight.objects.all().order_by('label')
        follower_data = []
        follows_data = []
        ff_data = []
        label_data = []
        for data in media_insight_data:
            follower_data.append(data.follower)
            follows_data.append(data.follows)
            ff = math.floor((data.follower / data.follows) * 100 / 100)
            ff_data.append(ff)
            label_data.append(data.label)

        like = 0
        comments = 0
        count = 1
        post_timestamp = ''
        for data in business_discovery['media']['data']:
            # 投稿日取得
            timestamp = localtime(datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S%z')).strftime('%Y-%m-%d')
            # 同じ日に複数の投稿がある場合、各データを足していく
            if post_timestamp == timestamp:
                like += data['like_count']
                comments += data['comments_count']
                count += 1
            else:
                like = data['like_count']
                comments = data['comments_count']
                post_timestamp = timestamp
                count = 1

            # 投稿データベースに保存
            obj, created = Post.objects.update_or_create(
                label=timestamp,
                defaults={
                    'like': like,
                    'comments': comments,
                    'count': count,
                }
            )

        # Postデーターベースからデータを取得
        # order_byで昇順に並び替え
        post_data = Post.objects.all().order_by("label")
        like_data = []
        comments_data = []
        count_data = []
        post_label_data = []
        for data in post_data:
            # いいね数
            like_data.append(data.like)
            # コメント数
            comments_data.append(data.comments)
            # 投稿数
            count_data.append(data.count)
            # ラベル
            post_label_data.append(data.label)

        # アカウントのインサイトデータ
        insight_data = {
            'follower_data': follower_data,
            'follows_data': follows_data,
            'ff_data': ff_data,
            'label_data': label_data,
            'like_data': like_data,
            'comments_data': comments_data,
            'count_data': count_data,
            'post_label_data': post_label_data,
        }
        latest_media_data = business_discovery['media']['data'][1]
        params['media_id'] = latest_media_data['id']
        media_response = get_media_insights(params)
        print(latest_media_data)
        media_data = media_response['json_data']['data']
        if latest_media_data['media_type'] == 'CAROUSEL_ALBUM':
            media_url = latest_media_data['children']['data'][0]['media_url']
            if latest_media_data['children']['data'][0]['media_type'] == 'VIDEO':
                media_type = 'VIDEO'
            else:
                media_type = 'IMAGE'
        else:
            media_url = latest_media_data['media_url']
            media_type = latest_media_data['media_type']

        insight_media_data = {
            'caption': latest_media_data['caption'] if 'caption' in latest_media_data  else 'キャプションなし',
            'media_type': media_type,
            'media_url': media_url,
            'permalink': latest_media_data['permalink'],
            'timestamp': localtime(datetime.strptime(latest_media_data['timestamp'], '%Y-%m-%dT%H:%M:%S%z')).strftime('%Y/%m/%d %H:%M'),
            'like_count': latest_media_data['like_count'],
            'comments_count': latest_media_data['comments_count'],
            'engagement': media_data[0]['values'][0]['value'],
            'impression': media_data[1]['values'][0]['value'],
            'reach': media_data[2]['values'][0]['value'],
            'save': media_data[3]['values'][0]['value'],
        }

        return render(request, 'app/index.html', {
            'today': today.strftime('%Y-%m-%d'),
            'account_data': account_data,
            'insight_data': json.dumps(insight_data),
            'insight_media_data': insight_media_data,
        })