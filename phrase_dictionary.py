"""
Local phrase dictionary for fast lookup.
Common Chinese-English expressions used in diary writing.
"""

PHRASE_DICTIONARY = {
    # 情感表达
    "很高兴认识你": {
        "translations": ["Nice to meet you", "Pleased to meet you", "Glad to meet you"],
        "examples": [
            "Nice to meet you. I've heard so much about you.",
            "It's a pleasure to meet you in person."
        ],
        "alternatives": ["Good to meet you", "Delighted to make your acquaintance"]
    },
    "恍然大悟": {
        "translations": ["Suddenly realize", "Have an epiphany", "See the light", "It dawned on me"],
        "examples": [
            "It suddenly dawned on me that I had left my keys at home.",
            "After hours of thinking, I finally had an epiphany about the solution."
        ],
        "alternatives": ["A lightbulb moment", "The penny dropped", "Realize all of a sudden"]
    },
    "心情很好": {
        "translations": ["In a good mood", "Feeling great", "In high spirits", "On cloud nine"],
        "examples": [
            "I'm in a good mood today because the sun is shining.",
            "She's been on cloud nine since she got the promotion."
        ],
        "alternatives": ["Feeling upbeat", "In a cheerful mood", "Walking on air"]
    },
    "心情很差": {
        "translations": ["In a bad mood", "Feeling down", "In low spirits", "Under the weather"],
        "examples": [
            "I'm feeling a bit down today.",
            "He's been in low spirits since the exam results came out."
        ],
        "alternatives": ["Feeling blue", "Down in the dumps", "Not in the mood"]
    },
    "非常生气": {
        "translations": ["Very angry", "Furious", "Mad", "Livid"],
        "examples": [
            "I was furious when I found out the truth.",
            "She was livid about the unfair treatment."
        ],
        "alternatives": ["Seeing red", "Blowing a fuse", "Flying off the handle"]
    },
    "感到惊讶": {
        "translations": ["Surprised", "Amazed", "Astonished", "Taken aback"],
        "examples": [
            "I was amazed by her talent.",
            "We were all taken aback by the sudden news."
        ],
        "alternatives": ["Caught off guard", "Blown away", "Stunned"]
    },
    "感到失望": {
        "translations": ["Disappointed", "Let down", "Disheartened"],
        "examples": [
            "I was disappointed with the movie.",
            "Don't let me down this time."
        ],
        "alternatives": ["Feeling deflated", "Crushed", "Heartbroken"]
    },
    "感到紧张": {
        "translations": ["Nervous", "Anxious", "Stressed", "On edge"],
        "examples": [
            "I'm so nervous about the interview tomorrow.",
            "She's been on edge all day waiting for the results."
        ],
        "alternatives": ["Butterflies in my stomach", "On pins and needles", "Wired"]
    },
    "感到放松": {
        "translations": ["Relaxed", "At ease", "Calm", "Peaceful"],
        "examples": [
            "I feel so relaxed after the yoga class.",
            "The peaceful music helped me calm down."
        ],
        "alternatives": ["Laid-back", "Chilled out", "Zen"]
    },
    "感到兴奋": {
        "translations": ["Excited", "Thrilled", "Ecstatic", "Pumped"],
        "examples": [
            "I'm so excited about the trip next week!",
            "She was thrilled to receive the invitation."
        ],
        "alternatives": ["Buzzing", "Hyped up", "Over the moon"]
    },
    "感到疲惫": {
        "translations": ["Tired", "Exhausted", "Worn out", "Drained"],
        "examples": [
            "I'm exhausted after the long hike.",
            "She felt completely drained after the meeting."
        ],
        "alternatives": ["Burned out", "Dead on my feet", "Ready to drop"]
    },
    "感到无聊": {
        "translations": ["Bored", "Uninterested", "Restless"],
        "examples": [
            "The lecture was so boring that I fell asleep.",
            "I'm getting restless sitting here all day."
        ],
        "alternatives": ["Fed up", "Sick and tired", "Climbing the walls"]
    },
    "感到害怕": {
        "translations": ["Scared", "Afraid", "Frightened", "Terrified"],
        "examples": [
            "I'm scared of heights.",
            "She was terrified of the thunderstorm."
        ],
        "alternatives": ["Petrified", "Shaking like a leaf", "Scared stiff"]
    },
    "感到尴尬": {
        "translations": ["Embarrassed", "Awkward", "Mortified"],
        "examples": [
            "I felt so embarrassed when I forgot her name.",
            "That awkward moment when you wave at someone who isn't waving at you."
        ],
        "alternatives": ["Cringing", "Wishing the ground would swallow me up", "Red-faced"]
    },
    "感到自豪": {
        "translations": ["Proud", "Accomplished", "Pleased with myself"],
        "examples": [
            "I'm proud of what we've achieved.",
            "She felt accomplished after finishing the marathon."
        ],
        "alternatives": ["Beaming with pride", "Patting myself on the back", "Walking tall"]
    },
    "感到感激": {
        "translations": ["Grateful", "Thankful", "Appreciative"],
        "examples": [
            "I'm grateful for all your help.",
            "I really appreciate your kindness."
        ],
        "alternatives": ["Can't thank you enough", "In your debt", "Owe you one"]
    },
    "感到困惑": {
        "translations": ["Confused", "Puzzled", "Baffled", "Perplexed"],
        "examples": [
            "I'm confused about what to do next.",
            "The instructions completely baffled me."
        ],
        "alternatives": ["At a loss", "Drawing a blank", "Can't make head or tail of it"]
    },
    "感到孤独": {
        "translations": ["Lonely", "Isolated", "Homesick"],
        "examples": [
            "I felt lonely in the new city.",
            "She gets homesick when she's away from family."
        ],
        "alternatives": ["Feeling blue", "Longing for company", "Missing home"]
    },
    "感到满足": {
        "translations": ["Satisfied", "Content", "Fulfilled"],
        "examples": [
            "I feel satisfied with my progress.",
            "She leads a content and peaceful life."
        ],
        "alternatives": ["At peace", "Happy with what I have", "Living the dream"]
    },
    # 日常活动
    "起床": {
        "translations": ["Get up", "Wake up", "Rise"],
        "examples": [
            "I usually get up at 7 AM.",
            "It's hard to wake up early on weekends."
        ],
        "alternatives": ["Roll out of bed", "Drag myself out of bed", "Rise and shine"]
    },
    "睡觉": {
        "translations": ["Go to bed", "Sleep", "Hit the hay"],
        "examples": [
            "I usually go to bed around 11 PM.",
            "I'm so tired, I'm going to hit the hay early tonight."
        ],
        "alternatives": ["Turn in", "Catch some Z's", "Crash"]
    },
    "吃早餐": {
        "translations": ["Have breakfast", "Eat breakfast"],
        "examples": [
            "I always have breakfast before work.",
            "Skipping breakfast makes me hungry all morning."
        ],
        "alternatives": ["Grab a bite", "Fuel up for the day", "Break my fast"]
    },
    "去上学": {
        "translations": ["Go to school", "Head to school", "Attend school"],
        "examples": [
            "I go to school by bus every day.",
            "She heads to school early to avoid traffic."
        ],
        "alternatives": ["Off to school", "Make my way to school", "Commute to school"]
    },
    "去工作": {
        "translations": ["Go to work", "Head to work", "Commute"],
        "examples": [
            "I go to work at 9 AM.",
            "The commute to work takes about an hour."
        ],
        "alternatives": ["Off to work", "Clock in", "Start my shift"]
    },
    "回家": {
        "translations": ["Go home", "Head home", "Return home"],
        "examples": [
            "I can't wait to go home and relax.",
            "She headed home immediately after class."
        ],
        "alternatives": ["Make my way home", "Get home", "Arrive home"]
    },
    "做作业": {
        "translations": ["Do homework", "Work on assignments"],
        "examples": [
            "I need to do my homework before dinner.",
            "She spent the whole evening working on her assignments."
        ],
        "alternatives": ["Hit the books", "Study", "Get my work done"]
    },
    "锻炼身体": {
        "translations": ["Exercise", "Work out", "Do sports"],
        "examples": [
            "I try to exercise every day.",
            "She works out at the gym three times a week."
        ],
        "alternatives": ["Get some exercise", "Train", "Stay active"]
    },
    "散步": {
        "translations": ["Take a walk", "Go for a walk", "Stroll"],
        "examples": [
            "I like to take a walk after dinner.",
            "We went for a walk in the park."
        ],
        "alternatives": ["Go for a stroll", "Walk around", "Stretch my legs"]
    },
    "看电视": {
        "translations": ["Watch TV", "Watch television"],
        "examples": [
            "I usually watch TV before bed.",
            "We spent the evening watching our favorite show."
        ],
        "alternatives": ["Binge-watch", "Catch up on shows", "Zone out in front of the TV"]
    },
    "看书": {
        "translations": ["Read a book", "Do some reading"],
        "examples": [
            "I love to read a book before sleep.",
            "She spent the afternoon doing some reading."
        ],
        "alternatives": ["Get lost in a book", "Read up on something", "Flip through a book"]
    },
    "玩游戏": {
        "translations": ["Play games", "Game"],
        "examples": [
            "The kids love to play games on weekends.",
            "I spent the evening gaming with friends."
        ],
        "alternatives": ["Have a gaming session", "Play video games", "Compete online"]
    },
    "做饭": {
        "translations": ["Cook", "Make dinner", "Prepare a meal"],
        "examples": [
            "I enjoy cooking for my family.",
            "She spent the afternoon preparing a special meal."
        ],
        "alternatives": ["Whip up something", "Get cooking", "Fix dinner"]
    },
    "打扫房间": {
        "translations": ["Clean the room", "Tidy up", "Do cleaning"],
        "examples": [
            "I need to clean my room this weekend.",
            "She spent the morning tidying up the house."
        ],
        "alternatives": ["Spring clean", "Declutter", "Straighten up"]
    },
    "购物": {
        "translations": ["Go shopping", "Shop"],
        "examples": [
            "I went shopping for new clothes.",
            "She loves to shop at the weekend."
        ],
        "alternatives": ["Browse the stores", "Pick up some things", "Retail therapy"]
    },
    "和朋友聚会": {
        "translations": ["Hang out with friends", "Meet up with friends", "Socialize"],
        "examples": [
            "I hung out with my friends at the cafe.",
            "We met up with some old friends for dinner."
        ],
        "alternatives": ["Catch up with friends", "Spend time with friends", "Get together"]
    },
    "和家人在一起": {
        "translations": ["Spend time with family", "Be with family"],
        "examples": [
            "I love spending time with my family.",
            "The holidays are for being with family."
        ],
        "alternatives": ["Family time", "Quality time with loved ones", "Bond with family"]
    },
    # 天气相关
    "天气很好": {
        "translations": ["The weather is nice", "Good weather", "Beautiful day"],
        "examples": [
            "The weather is nice today, let's go outside.",
            "What a beautiful day for a picnic!"
        ],
        "alternatives": ["Lovely weather", "Perfect day", "Sunny and warm"]
    },
    "天气很差": {
        "translations": ["Bad weather", "Terrible weather", "Awful weather"],
        "examples": [
            "The bad weather ruined our plans.",
            "What awful weather we're having!"
        ],
        "alternatives": ["Miserable weather", "Gloomy day", "Rainy and cold"]
    },
    "下雨": {
        "translations": ["It's raining", "Rain"],
        "examples": [
            "It's raining heavily outside.",
            "I forgot my umbrella and got caught in the rain."
        ],
        "alternatives": ["Pouring down", "Raining cats and dogs", "Drizzling"]
    },
    "下雪": {
        "translations": ["It's snowing", "Snow"],
        "examples": [
            "It's snowing! Everything looks so beautiful.",
            "The snow covered the ground overnight."
        ],
        "alternatives": ["Snowfall", "Blanketed in snow", "Whiteout"]
    },
    "刮风": {
        "translations": ["It's windy", "Windy"],
        "examples": [
            "It's so windy today, I can barely walk.",
            "The wind blew my hat away."
        ],
        "alternatives": ["Gusty", "Blowing a gale", "Howling wind"]
    },
    "阳光明媚": {
        "translations": ["Sunny", "Bright and sunny", "Sunshine"],
        "examples": [
            "It's a sunny day, perfect for outdoor activities.",
            "The bright sunshine lifted my spirits."
        ],
        "alternatives": ["Glorious sunshine", "Clear skies", "Sun-drenched"]
    },
    # 学习相关
    "努力学习": {
        "translations": ["Study hard", "Work hard"],
        "examples": [
            "I need to study hard for the exam.",
            "She's been working hard all semester."
        ],
        "alternatives": ["Hit the books", "Buckle down", "Put in the effort"]
    },
    "考试": {
        "translations": ["Exam", "Test", "Quiz"],
        "examples": [
            "I have an important exam tomorrow.",
            "The test was harder than I expected."
        ],
        "alternatives": ["Finals", "Midterms", "Assessment"]
    },
    "通过考试": {
        "translations": ["Pass the exam", "Ace the test"],
        "examples": [
            "I managed to pass the exam with a good score.",
            "She aced the test without even studying!"
        ],
        "alternatives": ["Get a good grade", "Pass with flying colors", "Nail the exam"]
    },
    "学习新东西": {
        "translations": ["Learn something new", "Pick up new skills"],
        "examples": [
            "I love learning something new every day.",
            "He's picking up new skills quickly."
        ],
        "alternatives": ["Broaden my horizons", "Expand my knowledge", "Get the hang of something"]
    },
    # 时间表达
    "今天早上": {
        "translations": ["This morning"],
        "examples": [
            "This morning, I woke up early.",
            "I had a meeting this morning."
        ],
        "alternatives": ["Earlier today", "In the morning", "At dawn"]
    },
    "今天下午": {
        "translations": ["This afternoon"],
        "examples": [
            "This afternoon, I'm going to the library.",
            "The rain started this afternoon."
        ],
        "alternatives": ["Later today", "After lunch", "In the afternoon"]
    },
    "今天晚上": {
        "translations": ["Tonight", "This evening"],
        "examples": [
            "Tonight, I'm staying home to relax.",
            "We have dinner plans this evening."
        ],
        "alternatives": ["After dark", "This night", "Before bed"]
    },
    "昨天": {
        "translations": ["Yesterday"],
        "examples": [
            "Yesterday was a busy day.",
            "I met an old friend yesterday."
        ],
        "alternatives": ["The day before", "Last day", "24 hours ago"]
    },
    "今天": {
        "translations": ["Today"],
        "examples": [
            "Today is going to be a great day!",
            "I have a lot to do today."
        ],
        "alternatives": ["This day", "Right now", "Currently"]
    },
    "明天": {
        "translations": ["Tomorrow"],
        "examples": [
            "Tomorrow is my birthday!",
            "I'll finish the work tomorrow."
        ],
        "alternatives": ["The next day", "Coming day", "In 24 hours"]
    },
    "最近": {
        "translations": ["Recently", "Lately"],
        "examples": [
            "Recently, I've been very busy.",
            "Lately, the weather has been unpredictable."
        ],
        "alternatives": ["These days", "Of late", "In recent times"]
    },
    "一直": {
        "translations": ["Always", "All the time", "Constantly"],
        "examples": [
            "I've always wanted to visit Paris.",
            "She's constantly working on new projects."
        ],
        "alternatives": ["Forever", "Non-stop", "Without fail"]
    },
    # 常用连接词
    "首先": {
        "translations": ["First", "Firstly", "To begin with"],
        "examples": [
            "First, let me introduce myself.",
            "To begin with, I want to thank everyone."
        ],
        "alternatives": ["First of all", "In the first place", "For starters"]
    },
    "然后": {
        "translations": ["Then", "Next", "After that"],
        "examples": [
            "Then, we went to the restaurant.",
            "After that, everything changed."
        ],
        "alternatives": ["Following that", "Subsequently", "Later on"]
    },
    "最后": {
        "translations": ["Finally", "Lastly", "In the end"],
        "examples": [
            "Finally, I finished the project.",
            "In the end, everything worked out."
        ],
        "alternatives": ["At last", "Eventually", "To wrap up"]
    },
    "总之": {
        "translations": ["In conclusion", "In summary", "All in all"],
        "examples": [
            "In conclusion, it was a great experience.",
            "All in all, I'm satisfied with the results."
        ],
        "alternatives": ["To sum up", "In short", "To put it briefly"]
    },
    "虽然": {
        "translations": ["Although", "Even though", "Though"],
        "examples": [
            "Although it was raining, we went out.",
            "Even though I was tired, I kept working."
        ],
        "alternatives": ["Despite the fact that", "While", "Whereas"]
    },
    "但是": {
        "translations": ["But", "However", "Yet"],
        "examples": [
            "I wanted to go, but I was too busy.",
            "However, there is one problem."
        ],
        "alternatives": ["Nevertheless", "On the other hand", "Still"]
    },
    "因为": {
        "translations": ["Because", "Since", "As"],
        "examples": [
            "I stayed home because I was sick.",
            "Since it's late, we should leave now."
        ],
        "alternatives": ["Due to", "Owing to", "On account of"]
    },
    "所以": {
        "translations": ["So", "Therefore", "Thus"],
        "examples": [
            "I was tired, so I went to bed early.",
            "Therefore, we decided to cancel the trip."
        ],
        "alternatives": ["As a result", "Consequently", "Hence"]
    },
    "例如": {
        "translations": ["For example", "For instance", "Such as"],
        "examples": [
            "I love fruits, for example, apples and bananas.",
            "Many countries, such as Japan, have high-speed trains."
        ],
        "alternatives": ["Like", "Namely", "To illustrate"]
    },
    "事实上": {
        "translations": ["In fact", "Actually", "As a matter of fact"],
        "examples": [
            "In fact, I used to live there.",
            "Actually, that's not quite right."
        ],
        "alternatives": ["To be honest", "Truth be told", "In reality"]
    },
    # 其他常用表达
    "慢慢来": {
        "translations": ["Take your time", "No rush"],
        "examples": [
            "Take your time, there's no hurry.",
            "No rush, we have plenty of time."
        ],
        "alternatives": ["At your own pace", "Don't rush", "Easy does it"]
    },
    "加油": {
        "translations": ["Go for it", "You can do it", "Keep it up"],
        "examples": [
            "Go for it! I believe in you.",
            "Keep it up, you're doing great!"
        ],
        "alternatives": ["Hang in there", "Don't give up", "Push through"]
    },
    "没关系": {
        "translations": ["It's okay", "Never mind", "No problem"],
        "examples": [
            "It's okay, don't worry about it.",
            "Never mind, it happens to everyone."
        ],
        "alternatives": ["Don't mention it", "It's all good", "No worries"]
    },
    "太好了": {
        "translations": ["Great", "Wonderful", "Fantastic"],
        "examples": [
            "That's great news!",
            "What a wonderful day!"
        ],
        "alternatives": ["Awesome", "Excellent", "Terrific"]
    },
    "真遗憾": {
        "translations": ["What a pity", "That's a shame", "Too bad"],
        "examples": [
            "What a pity you couldn't come.",
            "That's a shame, I was looking forward to it."
        ],
        "alternatives": ["Such a waste", "A real bummer", "How unfortunate"]
    },
    "我不知道": {
        "translations": ["I don't know", "I have no idea"],
        "examples": [
            "I don't know the answer.",
            "I have no idea what you're talking about."
        ],
        "alternatives": ["Beats me", "Your guess is as good as mine", "I'm clueless"]
    },
    "我明白了": {
        "translations": ["I see", "I understand", "Got it"],
        "examples": [
            "I see what you mean.",
            "Got it, thanks for explaining."
        ],
        "alternatives": ["That makes sense", "Crystal clear", "I'm with you"]
    },
    "我不明白": {
        "translations": ["I don't understand", "I'm confused"],
        "examples": [
            "I don't understand this question.",
            "I'm confused about what to do next."
        ],
        "alternatives": ["It's all Greek to me", "I'm lost", "Can you clarify?"]
    },
    "请稍等": {
        "translations": ["Please wait", "One moment", "Hold on"],
        "examples": [
            "Please wait, I'll be right back.",
            "Hold on, let me check."
        ],
        "alternatives": ["Just a second", "Bear with me", "Give me a minute"]
    },
    "再见": {
        "translations": ["Goodbye", "Bye", "See you"],
        "examples": [
            "Goodbye! Have a nice day.",
            "See you tomorrow!"
        ],
        "alternatives": ["Take care", "Catch you later", "So long"]
    },
    "祝你好运": {
        "translations": ["Good luck", "Best of luck"],
        "examples": [
            "Good luck on your exam!",
            "Best of luck with your new job!"
        ],
        "alternatives": ["Break a leg", "Fingers crossed", "Wish you success"]
    },
    "恭喜": {
        "translations": ["Congratulations", "Congrats"],
        "examples": [
            "Congratulations on your promotion!",
            "Congrats, you did it!"
        ],
        "alternatives": ["Well done", "Hats off to you", "Kudos"]
    },
    "谢谢": {
        "translations": ["Thank you", "Thanks"],
        "examples": [
            "Thank you for your help.",
            "Thanks a lot!"
        ],
        "alternatives": ["I appreciate it", "Much obliged", "You're a lifesaver"]
    },
    "对不起": {
        "translations": ["Sorry", "I'm sorry", "My apologies"],
        "examples": [
            "I'm sorry for being late.",
            "My apologies for the inconvenience."
        ],
        "alternatives": ["I apologize", "Pardon me", "Forgive me"]
    },
    "不客气": {
        "translations": ["You're welcome", "No problem"],
        "examples": [
            "You're welcome, happy to help.",
            "No problem at all!"
        ],
        "alternatives": ["My pleasure", "Don't mention it", "Anytime"]
    },
    "没关系": {
        "translations": ["It's okay", "Never mind", "No problem"],
        "examples": [
            "It's okay, don't worry about it.",
            "Never mind, it happens to everyone."
        ],
        "alternatives": ["Don't mention it", "It's all good", "No worries"]
    },

    # 日记写作常用表达
    "真是美好的一天": {
        "translations": ["What a wonderful day", "What a beautiful day", "Such a lovely day"],
        "examples": [
            "What a wonderful day! The sun is shining and everything feels perfect.",
            "It was such a lovely day that we decided to have a picnic."
        ],
        "alternatives": ["What a gorgeous day", "A truly beautiful day", "Couldn't ask for a better day"]
    },
    "非常开心": {
        "translations": ["Very happy", "Overjoyed", "Delighted", "Thrilled"],
        "examples": [
            "I was very happy to receive the good news.",
            "She was overjoyed when she saw the surprise."
        ],
        "alternatives": ["On cloud nine", "Walking on air", "Over the moon"]
    },
    "非常难过": {
        "translations": ["Very sad", "Heartbroken", "Devastated", "Upset"],
        "examples": [
            "I was very sad to hear the news.",
            "She felt heartbroken after saying goodbye."
        ],
        "alternatives": ["Down in the dumps", "Feeling blue", "In tears"]
    },
    "印象深刻": {
        "translations": ["Impressive", "Memorable", "Left a deep impression"],
        "examples": [
            "The view was truly impressive.",
            "It was a memorable experience that I will never forget."
        ],
        "alternatives": ["Unforgettable", "Striking", "Remarkable"]
    },
    "值得一去": {
        "translations": ["Worth visiting", "Well worth a visit", "A must-see"],
        "examples": [
            "The museum is definitely worth visiting.",
            "It's a must-see attraction in the city."
        ],
        "alternatives": ["Worth the trip", "Shouldn't be missed", "Highly recommended"]
    },
    "意犹未尽": {
        "translations": ["Want more", "Not ready to leave", "Wish it could last longer"],
        "examples": [
            "The trip was so good that I wanted more.",
            "I wasn't ready to leave — it was such a wonderful place."
        ],
        "alternatives": ["Left wanting more", "Didn't want it to end", "Could have stayed forever"]
    },
    "流连忘返": {
        "translations": ["Linger on without wanting to leave", "So captivated that one forgets to go home"],
        "examples": [
            "The scenery was so beautiful that I lingered on, not wanting to leave.",
            "I was so captivated by the place that I lost track of time."
        ],
        "alternatives": ["Couldn't tear myself away", "Lost in the moment", "Time stood still"]
    },
    "人山人海": {
        "translations": ["Huge crowds", "Packed with people", "A sea of people"],
        "examples": [
            "The tourist spot was packed with people.",
            "There was a sea of people at the festival."
        ],
        "alternatives": ["Shoulder to shoulder", "Wall-to-wall people", "Absolutely packed"]
    },
    "风景如画": {
        "translations": ["Picturesque", "Scenic", "Picture-perfect"],
        "examples": [
            "The village was picturesque, like something from a postcard.",
            "The scenic landscape took my breath away."
        ],
        "alternatives": ["Breathtaking views", "Postcard-perfect", "A sight to behold"]
    },
    "回味无穷": {
        "translations": ["Leave a lasting impression", "Memorable", "The taste lingers on"],
        "examples": [
            "The food was so delicious that the taste still lingers.",
            "The experience left a lasting impression on me."
        ],
        "alternatives": ["Unforgettable", "Hauntingly good", "The memory stays with you"]
    },
    "不虚此行": {
        "translations": ["The trip was well worth it", "It was worth the journey", "Not a wasted trip"],
        "examples": [
            "The trip was well worth it — I learned so much.",
            "It was definitely worth the journey just to see the sunset."
        ],
        "alternatives": ["Worth every mile", "Glad I made the trip", "No regrets at all"]
    },
    "太棒了": {
        "translations": ["Awesome", "Amazing", "Incredible", "Fantastic"],
        "examples": [
            "The concert was absolutely amazing!",
            "That's incredible news!"
        ],
        "alternatives": ["Mind-blowing", "Out of this world", "Spectacular"]
    },
    "太美了": {
        "translations": ["So beautiful", "Gorgeous", "Stunning", "Breathtaking"],
        "examples": [
            "The sunset was so beautiful.",
            "She looked absolutely stunning in that dress."
        ],
        "alternatives": ["Drop-dead gorgeous", "Picture-perfect", "Absolutely breathtaking"]
    },
    "太累了": {
        "translations": ["So tired", "Exhausted", "Worn out", "Dead tired"],
        "examples": [
            "I'm so tired after the long day.",
            "I was completely exhausted by the end of the hike."
        ],
        "alternatives": ["Dead on my feet", "Ready to collapse", "Running on fumes"]
    },
    "太好玩了": {
        "translations": ["So much fun", "A blast", "Really enjoyable"],
        "examples": [
            "The party was so much fun!",
            "We had a blast at the amusement park."
        ],
        "alternatives": ["A ton of fun", "Had the time of my life", "Absolutely loved it"]
    },
    "太贵了": {
        "translations": ["Too expensive", "Overpriced", "Costs a fortune"],
        "examples": [
            "The restaurant was too expensive for what you get.",
            "That jacket costs a fortune!"
        ],
        "alternatives": ["Way over budget", "Costs an arm and a leg", "Ridiculously pricey"]
    },
    "太远了": {
        "translations": ["Too far", "A long way", "Quite a distance"],
        "examples": [
            "The station is too far to walk.",
            "It's quite a distance from here to the city center."
        ],
        "alternatives": ["Miles away", "A real trek", "In the middle of nowhere"]
    },
    "期待已久": {
        "translations": ["Long-awaited", "Eagerly anticipated", "Been looking forward to"],
        "examples": [
            "The long-awaited concert finally arrived.",
            "I've been looking forward to this trip for months."
        ],
        "alternatives": ["Couldn't wait for", "Counted down the days", "Highly anticipated"]
    },
    "出乎意料": {
        "translations": ["Unexpected", "Surprising", "Beyond expectations"],
        "examples": [
            "The result was completely unexpected.",
            "The food was surprisingly good."
        ],
        "alternatives": ["Came out of nowhere", "Took me by surprise", "Blew my expectations"]
    },
    "大开眼界": {
        "translations": ["Eye-opening", "Broaden one's horizons", "A real eye-opener"],
        "examples": [
            "The trip was truly eye-opening.",
            "It really broadened my horizons."
        ],
        "alternatives": ["Mind-expanding", "Changed my perspective", "A learning experience"]
    },

    "明天很美好": {
        "translations": ["Tomorrow will be beautiful", "Tomorrow is going to be wonderful", "Tomorrow looks bright"],
        "examples": [
            "Tomorrow will be beautiful, I can feel it.",
            "Tomorrow looks bright with all these plans."
        ],
        "alternatives": ["Tomorrow is a new day", "The future is bright", "Looking forward to tomorrow"]
    },
    "今天很美好": {
        "translations": ["Today is beautiful", "Today is wonderful", "Today is a great day"],
        "examples": [
            "Today is beautiful, the sun is shining.",
            "Today is a great day for a walk."
        ],
        "alternatives": ["Today is lovely", "A beautiful day today", "Today couldn't be better"]
    },
    "昨天很美好": {
        "translations": ["Yesterday was beautiful", "Yesterday was wonderful"],
        "examples": [
            "Yesterday was beautiful, we had so much fun.",
            "Yesterday was a wonderful day spent with family."
        ],
        "alternatives": ["Yesterday was lovely", "A great day yesterday", "Yesterday was perfect"]
    },
    "今天很累": {
        "translations": ["Today was exhausting", "Today was tiring", "I'm so tired today"],
        "examples": [
            "Today was exhausting, I need some rest.",
            "I'm so tired today after all the work."
        ],
        "alternatives": ["Today wore me out", "A long day today", "Today drained me"]
    },
    "今天很开心": {
        "translations": ["Today was very happy", "Today was a joyful day", "I felt great today"],
        "examples": [
            "Today was very happy, everything went well.",
            "Today was a joyful day with all my friends."
        ],
        "alternatives": ["Today was amazing", "A wonderful day today", "Today was delightful"]
    },
    "今天很充实": {
        "translations": ["Today was fulfilling", "Today was productive", "Today was a full day"],
        "examples": [
            "Today was fulfilling, I got so much done.",
            "Today was a productive day at work."
        ],
        "alternatives": ["Today was packed", "A busy but good day", "Today was rewarding"]
    },
    
    "祝你有美好的一天": {
        "translations": ["Have a nice day", "Have a good day"],
        "examples": [
            "Have a nice day! See you tomorrow.",
            "Thanks, you too! Have a good day!"
        ],
        "alternatives": ["Enjoy your day", "Make it a great day", "Have a wonderful day"]
    },
}


def search_local_dictionary(phrase: str) -> dict:
    """
    Search the local phrase dictionary.
    Returns the result if found, None otherwise.
    Strategies: exact → longest partial → fuzzy → return None
    """
    # Strategy 1: Exact match
    if phrase in PHRASE_DICTIONARY:
        return {
            "phrase": phrase,
            **PHRASE_DICTIONARY[phrase],
            "source": "local"
        }
    
    # Strategy 2: Partial match — prefer the LONGEST matching key
    # (e.g. "太棒了" is a better match than "太" for "今天真是太棒了")
    # Rule: matched key must be >= 50% of query length, OR query is substring of key
    best_key = None
    best_key_len = 0
    for key, value in PHRASE_DICTIONARY.items():
        if key in phrase:
            # Key is substring of phrase: only accept if key is significant portion
            if len(key) >= len(phrase) * 0.5:
                if len(key) > best_key_len:
                    best_key = key
                    best_key_len = len(key)
                    best_value = value
        elif phrase in key and len(phrase) >= 2:
            # Phrase is substring of key: accept if phrase is meaningful (>= 2 chars)
            # (e.g. "太棒" matches "太棒了", but single char "美" does NOT match)
            if len(key) > best_key_len:
                best_key = key
                best_key_len = len(key)
                best_value = value
    
    if best_key:
        return {
            "phrase": best_key,
            **best_value,
            "source": "local"
        }
    
    # Strategy 3: Fuzzy match using SequenceMatcher (threshold >= 0.6)
    from difflib import SequenceMatcher
    best_key = None
    best_ratio = 0.0
    for key in PHRASE_DICTIONARY.keys():
        ratio = SequenceMatcher(None, phrase, key).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_key = key
    
    if best_key and best_ratio >= 0.6:
        value = PHRASE_DICTIONARY[best_key]
        return {
            "phrase": best_key,
            **value,
            "source": "local"
        }
    
    return None
