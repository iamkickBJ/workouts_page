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
  siteTitle: 'kick‘s Running Page', // 网站标题，您可以改成 "Kick Running" 之类的
  siteUrl: 'https://iamkickbj.github.io/workouts_page/', // 您的 GitHub Pages 地址
  logo: '/workouts_page/images/kick.jpg', // 👈 这里已经改成了您的新图片名
  description: 'Personal site and blog',
  keywords: 'workouts, running, cycling, riding, roadtrip, hiking, swimming',
  navLinks: [
    {
      name: 'Blog',
      url: 'https://iamkickbj.github.io/', // 博客链接，如果没博客可以填您的 GitHub 主页
    },
    {
      name: 'About',
      url: 'https://github.com/iamkickbj', // 关于页面，链接到您的 GitHub
    },
  ],
};

export default data;
