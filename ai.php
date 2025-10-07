<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Demo Modal</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #ffffff;
            min-height: 100vh;
            padding: 20px;
        }

        .demo-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .demo-btn {
            background:#245184;
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 18px;
            border-radius: 50px;
            cursor: pointer;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
            transition: all 0.3s ease;
            margin-bottom: 30px;
        }

        .demo-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.3);
        }

        .video-grid {
            display: none;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
            animation: fadeIn 0.5s ease-in;
        }

        .video-grid.active {
            display: grid;
        }

        .video-item {
            background: #245184;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }

        .video-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
            border-color: #245184;
        }

        .video-thumbnail {
            width: 100%;
            height: 200px;
            background: #245184;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 15px;
            position: relative;
        }

        .play-icon {
            width: 60px;
            height: 60px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            color: #333;
            transition: all 0.3s ease;
        }

        .video-item:hover .play-icon {
            transform: scale(1.1);
            background: white;
        }

        .video-title {
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 8px;
        }

        .video-description {
            color: #666;
            font-size: 14px;
            line-height: 1.4;
        }

        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.9);
            animation: fadeIn 0.3s ease;
        }

        .modal.active {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-content {
            position: relative;
            max-width: 80%;
            max-height: 80%;
            background: #000;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
            animation: slideIn 0.4s ease;
        }

        .close-btn {
            position: absolute;
            top: 15px;
            right: 20px;
            color: rgb(0, 0, 0);
            font-size: 35px;
            font-weight: bold;
            cursor: pointer;
            z-index: 1001;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: rgba(0, 0, 0, 0.5);
            transition: all 0.3s ease;
        }

        .close-btn:hover {
            background: rgb(255, 255, 255);
            transform: rotate(90deg);
        }

        .modal-video {
            width: 100%;
            height: auto;
            max-height: 70vh;
            display: block;
        }

        .video-info {
            padding: 20px;
            background: #245184;
            color: white;
        }

        .video-info h3 {
            font-size: 24px;
            margin-bottom: 10px;
        }

        .video-info p {
            font-size: 16px;
            line-height: 1.5;
            opacity: 0.9;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
            }

            to {
                opacity: 1;
            }
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: scale(0.7) translateY(-50px);
            }

            to {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
        }

        @media (max-width: 768px) {
            .modal-content {
                max-width: 95%;
                max-height: 90%;
            }

            .video-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>

<body>
    <div class="demo-container">


        <div style="text-align: center;">
            <button class="demo-btn" id="demoBtn" onclick="toggleDemo();">
                View Demo
            </button>
        </div>


        <div class="video-grid" id="videoGrid">
            <div class="video-item" onclick="openModal(1)">
                <div class="video-thumbnail" style="position: relative; width: 328px; height: 200px;">
                    <img src="../htdocs/training_videos/autop.png" alt="Video Thumbnail"
                        style="width: 100%; height: 100%; object-fit: cover;">
                    <div class="play-icon" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
              font-size: 48px; color: white; text-shadow: 0 0 10px rgba(0,0,0,0.7);">
                        ▶
                    </div>
                </div>

                <div class="video-title">Auto Point Cloud ShowHide</div>

            </div>

            <div class="video-item" onclick="openModal(2)">
                <div class="video-thumbnail" style="position: relative; width: 328px; height: 200px;">
                    <img src="../htdocs/training_videos/autor.png" alt="Video Thumbnail"
                        style="width: 100%; height: 100%; object-fit: cover;">
                    <div class="play-icon" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
              font-size: 48px; color: white; text-shadow: 0 0 10px rgba(0,0,0,0.7);">
                        ▶
                    </div>
                </div>

                <div class="video-title">Auto Room placement and tag</div>

            </div>

            <div class="video-item" onclick="openModal(3)">
                <div class="video-thumbnail" style="position: relative; width: 328px; height: 200px;">
                    <img src="../htdocs/training_videos/autosh.png" alt="Video Thumbnail"
                        style="width: 100%; height: 100%; object-fit: cover;">
                    <div class="play-icon" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
              font-size: 48px; color: white; text-shadow: 0 0 10px rgba(0,0,0,0.7);">
                        ▶
                    </div>
                </div>

                <div class="video-title">Auto Shadow Analysis</div>

            </div>

            <div class="video-item" onclick="openModal(4)">
                <div class="video-thumbnail" style="position: relative; width: 328px; height: 200px;">
                    <img src="../htdocs/training_videos/autoa.png" alt="Video Thumbnail"
                        style="width: 100%; height: 100%; object-fit: cover;">
                    <div class="play-icon" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
              font-size: 48px; color: white; text-shadow: 0 0 10px rgba(0,0,0,0.7);">
                        ▶
                    </div>
                </div>

                <div class="video-title">Auto Sheet Creation</div>

            </div>

            <div class="video-item" onclick="openModal(5)">
                <div class="video-thumbnail" style="position: relative; width: 328px; height: 200px;">
                    <img src="../htdocs/training_videos/autow.png" alt="Video Thumbnail"
                        style="width: 100%; height: 100%; object-fit: cover;">
                    <div class="play-icon" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
              font-size: 48px; color: white; text-shadow: 0 0 10px rgba(0,0,0,0.7);">
                        ▶
                    </div>
                </div>

                <div class="video-title">Auto Wall Alignment</div>

            </div>
        </div>
    </div>


    <!-- Modal -->
    <div class="modal" id="videoModal">
        <div class="modal-content">
            <span class="close-btn" onclick="closeModal()">&times;</span>
            <video class="modal-video" id="modalVideo" controls>
                <source src="" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            <div class="video-info" id="videoInfo">
                <h3 id="modalTitle">Video Title</h3>
                <p id="modalDescription">Video description goes here...</p>
            </div>
        </div>
    </div>
    <script>
        const videoData = {
            1: {
                title: "Auto Point Cloud ShowHide",
                videoUrl: "../htdocs/training_videos/Auto_Point_Cloud_Show_Hide.mp4",
            },
            2: {
                title: "Auto Room placement and tag",
                videoUrl: "../htdocs/training_videos/Auto_Room_Placement_and_Tag.mp4"
            },
            3: {
                title: "Auto Shadow Analysis",
                videoUrl: "../htdocs/training_videos/Auto_Shadow_Analysis.mp4"
            },
            4: {
                title: "Auto Sheet Creation",
                videoUrl: "../htdocs/training_videos/Auto_Sheet_Creation.mp4"
            },
            5: {
                title: "Auto Wall Alignment",
                videoUrl: "../htdocs/training_videos/Auto_Wall_Alignment.mp4"
            }
        };

        let isDemoOpen = false;

        function toggleDemo() {
            const videoGrid = document.getElementById('videoGrid');
            const demoBtn = document.getElementById('demoBtn');

            if (!isDemoOpen) {
               
                videoGrid.classList.add('active');
                demoBtn.innerHTML = 'Close Demo';
                demoBtn.style.background = '#245184';
                isDemoOpen = true;

               
                setTimeout(() => {
                    videoGrid.scrollIntoView({ behavior: 'smooth' });
                }, 100);
            } else {
                
                videoGrid.classList.remove('active');
                demoBtn.innerHTML = ' View Demo';
                demoBtn.style.background ='#245184';
                isDemoOpen = false;

           
                demoBtn.scrollIntoView({ behavior: 'smooth' });
            }
        }

        function launchDemo() {
            if (!isDemoOpen) {
                toggleDemo();
            }
        }

        function openModal(videoId) {
            const modal = document.getElementById('videoModal');
            const video = document.getElementById('modalVideo');
            const title = document.getElementById('modalTitle');
            const description = document.getElementById('modalDescription');

            const data = videoData[videoId];

            title.textContent = data.title;
            description.textContent = data.description;
            video.src = data.videoUrl;

            modal.classList.add('active');

         
            document.body.style.overflow = 'hidden';
        }

        function closeModal() {
            const modal = document.getElementById('videoModal');
            const video = document.getElementById('modalVideo');

            modal.classList.remove('active');
            video.pause();
            video.currentTime = 0;

     
            document.body.style.overflow = 'auto';
        }


        window.onclick = function (event) {
            const modal = document.getElementById('videoModal');
            if (event.target === modal) {
                closeModal();
            }
        }

     
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                closeModal();
            }
        });


        document.getElementById('videoModal').addEventListener('animationend', function () {
            if (!this.classList.contains('active')) {
                const video = document.getElementById('modalVideo');
                video.pause();
            }
        });
    </script>
</body>

</html>