using Microsoft.AspNetCore.Mvc;
using DemandForecastingA.Models;
using Newtonsoft.Json;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.IO;
using CsvHelper;
using System.Globalization;
using System.Data;

namespace DemandForecastingA.Controllers
{
    public class ForecastController : Controller
    {
        private readonly HttpClient _httpClient;

        public ForecastController(IHttpClientFactory httpClientFactory)
        {
            _httpClient = httpClientFactory.CreateClient();
        }

        // 1. Page Index (upload CSV)
        public IActionResult Index()
        {
            return View();
        }

        // 2. Upload CSV et redirection vers DataExplorer
        [HttpPost]
        public async Task<IActionResult> Index(IFormFile file)
        {
            if (file == null || file.Length == 0)
            {
                ViewBag.Error = "Please upload a CSV file.";
                return View();
            }

            var tempFileName = Path.Combine(Path.GetTempPath(), $"{Guid.NewGuid()}.csv");

            using (var stream = new FileStream(tempFileName, FileMode.Create))
            {
                await file.CopyToAsync(stream);
            }

            TempData["CsvPath"] = tempFileName;
            TempData.Keep("CsvPath");

            return RedirectToAction("DataExplorer");
        }

        // 3. Explorer CSV et choisir période
        public IActionResult DataExplorer()
        {
            if (TempData["CsvPath"] == null)
                return RedirectToAction("Index");

            var csvPath = TempData["CsvPath"].ToString();
            TempData.Keep("CsvPath");

            var dt = new DataTable();
            using (var reader = new StreamReader(csvPath))
            using (var csv = new CsvHelper.CsvReader(reader, CultureInfo.InvariantCulture))
            {
                using (var dr = new CsvHelper.CsvDataReader(csv))
                {
                    dt.Load(dr);
                }
            }

            return View(dt);
        }

        // 4. Dashboard avec prédictions pour tous les produits
        [HttpPost]
        public async Task<IActionResult> Dashboard(int period)
        {
            if (TempData["CsvPath"] == null)
                return RedirectToAction("Index");

            var csvPath = TempData["CsvPath"].ToString();
            TempData.Keep("CsvPath");

            var csvContent = await System.IO.File.ReadAllTextAsync(csvPath);
            var startDate = System.DateTime.Today.ToString("yyyy-MM-dd");
            var endDate = System.DateTime.Today.AddDays(period).ToString("yyyy-MM-dd");

            var requestData = new
            {
                csv_data = csvContent,
                start_date = startDate,
                end_date = endDate
            };

            var content = new StringContent(JsonConvert.SerializeObject(requestData), Encoding.UTF8, "application/json");

            try
            {
                var response = await _httpClient.PostAsync("http://127.0.0.1:5000/predict", content);
                if (!response.IsSuccessStatusCode)
                {
                    ViewBag.Error = "API error: " + response.StatusCode;
                    return View(new Dictionary<string, List<Prediction>>());
                }

                var jsonResponse = await response.Content.ReadAsStringAsync();
                var predictions = JsonConvert.DeserializeObject<Dictionary<string, List<Prediction>>>(jsonResponse);

                // ✅ Sauvegarder les prédictions pour le téléchargement
                TempData["Predictions"] = JsonConvert.SerializeObject(predictions);
                TempData.Keep("Predictions");

                return View(predictions);
            }
            catch (System.Exception ex)
            {
                ViewBag.Error = "Error connecting to API: " + ex.Message;
                return View(new Dictionary<string, List<Prediction>>());
            }
        }

        // 5. Télécharger toutes les prédictions en CSV
        public IActionResult DownloadAllPredictions()
        {
            if (!TempData.ContainsKey("Predictions"))
                return NotFound("Aucune prédiction disponible.");

            // Récupérer les prédictions JSON depuis TempData
            var json = TempData["Predictions"] as string;
            var allPredictions = JsonConvert.DeserializeObject<Dictionary<string, List<Prediction>>>(json);

            if (allPredictions == null || allPredictions.Count == 0)
                return NotFound("Aucune prédiction disponible.");

            var sb = new StringBuilder();
            sb.AppendLine("Product,Date,Units Sold");

            foreach (var kvp in allPredictions)
            {
                var product = kvp.Key;
                var predictions = kvp.Value;

                foreach (var p in predictions)
                {
                    sb.AppendLine($"{product},{p.ds},{p.Final_Hybrid}");
                }
            }

            var bytes = Encoding.UTF8.GetBytes(sb.ToString());
            return File(bytes, "text/csv", "All_Predictions.csv");
        }

        [HttpPost]
        public async Task<IActionResult> FiltredDashboard([FromBody] FilterRequest request)
        {
            try
            {
                if (request == null)
                {
                    return BadRequest(new { error = "Le body JSON est vide ou mal formé." });
                }
                Console.WriteLine("➡️ StartDate = " + request.StartDate);
                Console.WriteLine("➡️ EndDate = " + request.EndDate);
                Console.WriteLine("➡️ Products = " + string.Join(",", request.Products ?? new List<string>()));

                if (TempData["CsvPath"] == null)
                    return Json(new { error = "CsvPath not found in TempData" });

                // 🔹 Lire CSV depuis TempData si besoin
                var csvPath = TempData["CsvPath"].ToString();
                TempData.Keep("CsvPath");

                // 🔹 Construire le JSON pour l’API Python
                var csvContent = await System.IO.File.ReadAllTextAsync(csvPath);

                var requestData = new
                {
                    csv_data = csvContent,   // ⚡ on lit le vrai CSV côté serveur
                    start_date = request.StartDate,
                    end_date = request.EndDate,
                    products = request.Products
                };

                var content = new StringContent(JsonConvert.SerializeObject(requestData), Encoding.UTF8, "application/json");
                var response = await _httpClient.PostAsync("http://127.0.0.1:5000/predict", content);

                if (!response.IsSuccessStatusCode)
                    return Json(new { error = "API error: " + response.StatusCode });

                var jsonResponse = await response.Content.ReadAsStringAsync();
                var predictions = JsonConvert.DeserializeObject<Dictionary<string, List<Prediction>>>(jsonResponse);

                TempData["Predictions"] = JsonConvert.SerializeObject(predictions);
                TempData.Keep("Predictions");

                return Json(predictions);
            }
            catch (Exception ex)
            {
                return Json(new { error = "Server exception: " + ex.Message });
            }
        }

        public class FilterRequest
        {
            public string Data { get; set; }           // ✅ CSV data
            public string StartDate { get; set; }
            public string EndDate { get; set; }
            public List<string> Products { get; set; }
        }




    }
}
