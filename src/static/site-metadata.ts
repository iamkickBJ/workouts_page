interface ISiteMetadataResult {
  siteTitle: string;
  siteUrl: string;
  description: string;
  keywords: string;
  logo: string;
  navLinks: {
    name: string;
    url: string;
  }[];
}

const data: ISiteMetadataResult = {
  siteTitle: 'Kick 的运动记录', // 网站标题，您可以改成 "Kick Running" 之类的
  siteUrl: 'https://iamkickbj.github.io/workouts_page/', // 您的 GitHub Pages 地址
  logo: '/workouts_page/images/kick.jpg', // 👈 这里已经改成了您的新图片名
  description: 'Kick 的跑步、骑行与户外运动记录',
  keywords: '运动记录, 跑步, 骑行, 虚拟骑行, 徒步, 游泳, 户外',
  navLinks: [
    {
      name: '关于',
      url: 'https://github.com/iamkickbj', // 关于页面，链接到您的 GitHub
    },
  ],
};

export default data;
